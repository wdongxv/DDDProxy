# -*- coding: UTF-8 -*-
'''
Created on 2015年9月6日

@author: dxw
'''
import json
import math
import os
import random
import socket
import ssl
import threading
import time

from baseServer import sockConnect
from configFile import configFile
import log
from settingConfig import settingConfig
from symmetryConnectServerHandler import symmetryConnect
from symmetryConnectServerHandler import symmetryConnectServerHandler


maxConnectByOnServer = 2
remoteConnectMaxTime = 0
class localSymmetryConnect(symmetryConnect):
	def __init__(self, server):
		symmetryConnect.__init__(self, server)
		self.serverAuthPass = False
		
	def onServerAuthPass(self):
		pass
	def setServerAuthPass(self):
		self.serverAuthPass = True
		self.onServerAuthPass()
	
class remoteServerConnecter(symmetryConnectServerHandler):
	def __init__(self, server, authCode, *args, **kwargs):
		symmetryConnectServerHandler.__init__(self, server, *args, **kwargs)
		self.authPass = False
		self.authCode = authCode
	def onServerToServerMessage(self, serverMessage):
		opt = serverMessage["opt"]
		if opt == "auth":
			if serverMessage["status"] == "ok":
				for connect in self.symmetryConnectList.values():
					self.server.addCallback(connect.setServerAuthPass)
				self.authCallbackList = []
				self.authPass = True
				self.connectName = "[remote:%d]	%s" % (self.fileno(), self.addressStr())
			else:
				self.close()
		else:
			symmetryConnectServerHandler.onServerToServerMessage(self, serverMessage)
	def addLocalRealConnect(self, connect):
		self.addSymmetryConnect(connect, self.makeSymmetryConnectId())
		if self.authPass:
			self.server.addCallback(connect.setServerAuthPass)
	def auth(self):
		timenum = math.floor(time.time())
		data = {"opt":"auth"}
		data.update(symmetryConnectServerHandler.authMake(self.authCode, timenum))
		self.sendData(symmetryConnectServerHandler.serverToServerJsonMessageConnectId, json.dumps(data))
	def onClose(self):
		symmetryConnectServerHandler.onClose(self)
		localToRemoteConnectManger.manager.onConnectClose(self)
	def requestIdleClose(self):
		if self in localToRemoteConnectManger.manager.remoteConnectList:
			return
		symmetryConnectServerHandler.requestIdleClose(self)
	def fetchRemoteCert(self, remoteServerHost, remoteServerPort):
		ok = False
		remoteServerConnecter._createCertLock.acquire()
		certPath = self.SSLLocalCertPath(remoteServerHost, remoteServerPort)
		try:
			if not os.path.exists(certPath):
				cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerPort))
				f = open(certPath, "wt")
				f.write(cert)
				f.close()
			ok = True
		except:
			log.log(3, remoteServerHost, remoteServerPort)
		remoteServerConnecter._createCertLock.release()
		return ok
	def _initSocket(self, addr):
		if self.fetchRemoteCert(addr[0], addr[1]):
			try:
				sock = ssl.wrap_socket(
							sock	=		socket.socket(socket.AF_INET, socket.SOCK_STREAM),
							ca_certs	=	self.SSLLocalCertPath(addr[0], addr[1]),
							cert_reqs	=	ssl.CERT_REQUIRED)
				sock.connect(addr)
				cert = sock.getpeercert()
				subject = dict(x[0] for x in cert['subject'])
				commonName = subject["commonName"].encode('utf-8')
				authObj = commonName.split("_")
				certMakeTime = int(authObj[0])
				if time.time() - certMakeTime < 86400*15:
					makeAuth = symmetryConnectServerHandler.authMake(self.authCode, certMakeTime)
					if  authObj [1] == makeAuth["password"]:
						return sock
			except Exception as e:
				log.log(3, addr)
			self.deleteRemoteCert(addr[0], addr[1])
			try:
				sock.close()
			except:
				pass
		return None
	def SSLLocalCertPath(self, remoteServerHost, remoteServerPort):
		return configFile.makeConfigFilePathName("%s-%d.pem" % (remoteServerHost, remoteServerPort))
	def deleteRemoteCert(self, remoteServerHost, remoteServerPort):
		remoteServerConnecter._createCertLock.acquire()
		certPath = self.SSLLocalCertPath(remoteServerHost, remoteServerPort)
		if os.path.exists(certPath):
			os.unlink(certPath)
		remoteServerConnecter._createCertLock.release()
	_createCertLock = threading.RLock()



class localToRemoteConnectManger():
	def __init__(self, server):
		"""
		@param server: _baseServer
		"""
		self.server = server;
		self.remoteConnectList = []
		self.server.addDelay(1, self.handlerRemoteConnects)
	def get(self):
		"""
		@return: remoteServerConnectLocalHander
		"""
		remoteConnect = None
		
		for connect in self.remoteConnectList:
			if (not remoteConnect or len(remoteConnect.symmetryConnectList) > len(connect.symmetryConnectList)) and not connect.slowConnectStatus:
				remoteConnect = connect

		if not remoteConnect:
			remoteConnect = self.addRemoteConnect()
		return remoteConnect
	
	def addRemoteConnect(self):
		remoteServerList = settingConfig.setting(settingConfig.remoteServerList)
		if remoteServerList == None:
			return None
		
		remoteServer = random.choice(remoteServerList)
		remoteConnect = remoteServerConnecter(self.server, remoteServer["auth"])
		
		def connectDone(ok):
			if ok:
				remoteConnect.auth()
			
		port = int(remoteServer["port"]) if remoteServer["port"] else 8082
		remoteConnect.connect((remoteServer["host"], port), connectDone)
		self.remoteConnectList.append(remoteConnect);
		return remoteConnect
	def handlerRemoteConnects(self):
		remoteServerList = settingConfig.setting(settingConfig.remoteServerList)
		if remoteServerList == None:
			return None
		removeConnectList = []
		for remoteConnect in self.remoteConnectList:
			requestRemove = True
			for remoteServer in remoteServerList:
				port = int(remoteServer["port"]) if remoteServer["port"] else 8082
				if(remoteServer['host'] == remoteConnect.address[0] and port == remoteConnect.address[1]):
					requestRemove = False
					break
			if (not remoteConnect.connectStatus()) or (remoteConnect.info["startTime"] + max(remoteConnectMaxTime, 600) < time.time()) or requestRemove or remoteConnect.slowConnectStatus:
				removeConnectList.append(remoteConnect)
		for remoteConnect in removeConnectList:
			self.remoteConnectList.remove(remoteConnect)
			remoteConnect.requestIdleClose();
		
		for _ in range(maxConnectByOnServer):
			if maxConnectByOnServer > len(self.remoteConnectList):
				self.addRemoteConnect()
		self.server.addDelay(10, self.handlerRemoteConnects)
		
	def onConnectClose(self, connect):
		if connect in self.remoteConnectList:
			self.remoteConnectList.remove(connect)

	manager = None
	@staticmethod
	def install(server):
		if not localToRemoteConnectManger.manager:
			localToRemoteConnectManger.manager = localToRemoteConnectManger(server)
	@staticmethod
	def getConnectHost(host, port):
		port = port if port else 8082
		for connet in localToRemoteConnectManger.manager.remoteConnectList:
			if connet.address[0] == host and connet.address[1] == port:
				return connet
		return None
		
	@staticmethod
	def getConnect():
		"""
		@return: remoteServerConnectLocalHander
		"""
		return localToRemoteConnectManger.manager.get()
	
