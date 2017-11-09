# -*- coding: UTF-8 -*-
'''
Created on 2015年9月6日

@author: dxw
'''
from settingConfig import settingConfig
import math
import time
from symmetryConnectServerHandler import symmetryConnectServerHandler
import json
from DDDProxy.symmetryConnectServerHandler import symmetryConnect
import random

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
	def __init__(self, server, *args, **kwargs):
		symmetryConnectServerHandler.__init__(self, server, *args, **kwargs)
		self.authPass = False
	def onServerToServerMessage(self, serverMessage):
		opt = serverMessage["opt"]
		if opt == "auth":
			if serverMessage["status"] == "ok":
				for connect in self.symmetryConnectList.values():
					self.server.addCallback(connect.setServerAuthPass)
				self.authCallbackList = []
				self.authPass = True
				self.connectName = "[remote:%d]	%s(%s)" % (self.fileno(), self.address[0], self.addressIp)
			else:
				self.close()
		else:
			symmetryConnectServerHandler.onServerToServerMessage(self, serverMessage)
	def addLocalRealConnect(self, connect):
		self.addSymmetryConnect(connect, self.makeSymmetryConnectId())
		if self.authPass:
			self.server.addCallback(connect.setServerAuthPass)
	def auth(self, auth):
		timenum = math.floor(time.time())
		data = {"opt":"auth"}
		data.update(self.authMake(auth, timenum))
		self.sendData(symmetryConnectServerHandler.serverToServerJsonMessageConnectId, json.dumps(data))
	def onClose(self):
		symmetryConnectServerHandler.onClose(self)
		localToRemoteConnectManger.manager.onConnectClose(self)
	def requestIdleClose(self):
		if self in localToRemoteConnectManger.manager.remoteConnectList:
			return
		symmetryConnectServerHandler.requestIdleClose(self)
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
			if not remoteConnect or remoteConnect.info["pingSpeed"] > connect.info["pingSpeed"]:
				remoteConnect = connect

		if not remoteConnect:
			remoteConnect = self.addRemoteConnect()
		return remoteConnect
	
	def addRemoteConnect(self):
		remoteServerList = settingConfig.setting(settingConfig.remoteServerList)
		if remoteServerList == None:
			return None
		
		remoteConnect = remoteServerConnecter(self.server)
		remoteServer = random.choice(remoteServerList)
		
		def connectDone(ok):
			if ok:
				remoteConnect.auth(remoteServer["auth"])
			
		port = int(remoteServer["port"]) if remoteServer["port"] else 8082
		remoteConnect.connect((remoteServer["host"], port), True, connectDone)
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
	
