# -*- coding: UTF-8 -*-
'''
Created on 2015年9月6日

@author: dxw
'''
import threading
import os
import ssl
from settingConfig import settingConfig
import socket
from remoteServerHandler import remoteServerConnect
from baseServer import baseServer
import math
import time

createCertLock = threading.RLock()

class remoteServerConnectLocalHander(remoteServerConnect):
	def __init__(self, server, *args, **kwargs):
		remoteServerConnect.__init__(self, server, *args, **kwargs)
		self.authCallbackList = []
		self.authPass = False
		

	def onOpt(self, connectId, opt):
		if opt == remoteServerConnect.optAuthOK:
			if connectId == -1:
				for cb in self.authCallbackList:
					self.server.addCallback(cb,connect=self)
				self.authCallbackList = []
				self.authPass = True
		elif opt == remoteServerConnect.optAuthError:
			self.close()
# 		elif opt == remoteServerConnect.optCloseConnect:
# 			self.close()
		super(remoteServerConnectLocalHander, self).onOpt(connectId,opt)
# 		baseServer.log(2,"onOpt",connectId,opt)
	def auth(self,auth):
		randomNum = math.floor(time.time())
		self.sendData(-1,self.authMake(auth, randomNum))
	def addAuthCallback(self,cb):
		if self.authPass:
			self.server.addCallback(cb,connect=self)
		else:
			self.authCallbackList.append(cb)

class remoteConnectManger():
	"""
	@param manager: remoteConnectManger
	"""
	def __init__(self,server):
		self.server = server;
		self.remoteConnectList = []
		self.remoteConnectListLoop = 0
	def SSLLocalCertPath(self,remoteServerHost,remoteServerPort):
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
			self.getConnectCallback.pop(0)(self._getAuthedConnect())

	def getConnectWithLoop(self):
		if self.count()==0:
			return None
		self.remoteConnectListLoop += 1;
		if self.remoteConnectListLoop >= self.count():
			self.remoteConnectListLoop = 0
		connect = self.remoteConnectList[self.remoteConnectListLoop]
		return connect
	def count(self):
		return len(self.remoteConnectList)
	
	def onConnectClose(self,connect):
		self.remoteConnectList.remove(connect)
	def onConnectAuth(self,connect):
		pass
	def get(self):
		"""
		@return: remoteServerConnectLocalHander
		"""
		connect = self.getConnectWithLoop()
		if self.count() < 10:
			host,port,auth = settingConfig.setting(settingConfig.remoteServerKey)
			if host and auth and self.fetchRemoteCert(host, port):
				try:
					remoteSocket = ssl.wrap_socket(
						sock	=		socket.socket(socket.AF_INET, socket.SOCK_STREAM), 
						ca_certs	=	self.SSLLocalCertPath(host,port),
						cert_reqs	=	ssl.CERT_REQUIRED)		
					connect = remoteServerConnectLocalHander(self.server)
					remoteSocket.connect((host,port))
					connect.connect(remoteSocket,(host,port))
					connect.auth(auth)
					connect.addAuthCallback(self.onConnectAuth)
					connect.setConnectCloseCallBack(-1,self.onConnectClose)
					self.remoteConnectList.append(connect)
				except:
					baseServer.log(3)
					return None
		return connect;
	manager = None
	@staticmethod
	def install(server):
		if not remoteConnectManger.manager:
			remoteConnectManger.manager = remoteConnectManger(server)
	@staticmethod
	def getConnect():
		"""
		@return: remoteServerConnectLocalHander
		"""
		return remoteConnectManger.manager.get()
	