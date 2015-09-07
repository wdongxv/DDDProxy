# -*- coding: UTF-8 -*-
'''
Created on 2015年9月6日

@author: dxw
'''
import threading
import os
import ssl
from DDDProxy2.settingConfig import settingConfig
import socket
from DDDProxy2.remoteServerHandler import remoteServerConnect

createCertLock = threading.RLock()

class remoteConnectManger():
	def __init__(self):
		self.remoteConnectList = []
		self.remoteConnectListLoop = 0
	def SSLLocalCertPah(self,remoteServerHost,remoteServerPort):
		return "/tmp/dddproxy_cert.%s-%d.pem"%(remoteServerHost,remoteServerPort)
	def fetchRemoteCert(self,remoteServerHost,remoteServerPort):
		ok = False
		createCertLock.acquire()
		try:
			if not os.path.exists(self.SSLLocalCertPath(remoteServerHost,remoteServerPort)):
				cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerPort))
				open(self.SSLLocalCertPath(remoteServerHost,remoteServerPort), "wt").write(cert)
			ok = True
		except:
			pass
		createCertLock.release()
		return ok
	def _remoteServerConnected(self,connect,authOk):
		while len(self.getConnectCallback)>0:
			self.getConnectCallback.pop()(self._getAuthedConnect())

	def _getAuthedConnect(self):
		self.remoteConnectListLoop += 1;
		if self.remoteConnectListLoop >= self.count():
			self.remoteConnectListLoop = 0
		for i in range(self.count()):
			index = (i+self.remoteConnectListLoop)%self.count()
			connect = self.remoteConnectListLoop[index]
			if connect.authPass:
				return connect
		return None
	def count(self):
		return len(self.remoteConnectList)
	def get(self,callback):
		connect = self._getAuthedConnect()
		if connect:
			callback(connect)
			callback = None

		if self.count() >= 10:
			def remoteServerConnected(connect,authOk):
				if not authOk:
					self.remoteConnectList.remove(connect)
				if callback:
					callback(connect if authOk else None)
					
			host,port,auth = settingConfig.setting()[settingConfig.remoteServerKey]
			if host and auth and self.fetchRemoteCert(host, port):
				try:
					remoteSocket = ssl.wrap_socket(
						sock	=		socket.socket(socket.AF_INET, socket.SOCK_STREAM), 
						ca_certs	=	self.SSLLocalCertPath(host,port),
						cert_reqs	=	ssl.CERT_REQUIRED)		
					remoteSocket.connect((host,port))
					connect = remoteServerConnect(remoteSocket)
					connect.auth(auth,remoteServerConnected)
					self.remoteConnectList.append(connect)
					return
				except:
					pass
		if callback:
			callback(None)

		
	manager = None
	@staticmethod
	def getConnect(callback):
		if not remoteConnectManger.manager:
			remoteConnectManger.manager = remoteConnectManger()
		m = remoteConnectManger.manager
		m.get(callback)