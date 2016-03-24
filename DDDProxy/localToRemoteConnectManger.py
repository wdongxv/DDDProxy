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
				self.connectName = "[remote:" + str(self.fileno()) + "]	" + self.address[0]
				
			else:
				self.close()
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

class localToRemoteConnectManger():
	"""
	"""
	def __init__(self, server):
		self.server = server;
		self.remoteConnectList = {}
		self.remoteConnectListLoop = 0
	def get(self):
		"""
		@return: remoteServerConnectLocalHander
		"""
		self.remoteConnectListLoop += 1;
		remoteServerList = settingConfig.setting(settingConfig.remoteServerList)
		if remoteServerList == None:
			return None
		if self.remoteConnectListLoop >= len(remoteServerList) * maxConnectByOnServer:
			self.remoteConnectListLoop = 0
		i = 0
		for remoteServer in remoteServerList:
			connectList = None
			port = int(remoteServer["port"]) if remoteServer["port"] else 8082
			remoteServerKey = remoteServer["host"] + ":" + str(port)
			if remoteServerKey in self.remoteConnectList:
				connectList = self.remoteConnectList[remoteServerKey]
			else:
				self.remoteConnectList[remoteServerKey] = connectList = {}
				
			if  self.remoteConnectListLoop >= i and self.remoteConnectListLoop < i + maxConnectByOnServer:
				index = self.remoteConnectListLoop - i
				connect = None
				if index in connectList:
					connect = connectList[index]
					if (not connect.connectStatus()) or (connect.info["startTime"] + max(remoteConnectMaxTime, 600) < time.time()):
						connect = None
				if not connect:
					connect = remoteServerConnecter(self.server)
					connect.connect((remoteServer["host"], port), True)
					connect.auth(remoteServer["auth"])
					connectList[index] = connect
				return connect
			i += maxConnectByOnServer
		return None
	def onConnectClose(self, connect):
		for _, connectList in self.remoteConnectList.items():
			for k, v in connectList.items():
				if v == connect:
					del connectList[k]
					return

	manager = None
	@staticmethod
	def install(server):
		if not localToRemoteConnectManger.manager:
			localToRemoteConnectManger.manager = localToRemoteConnectManger(server)
	@staticmethod
	def getConnectHost(host, port):
		port = port if str(port) else "8082"
		return localToRemoteConnectManger.manager.remoteConnectList[host + ":" + port]
		
	@staticmethod
	def getConnect():
		"""
		@return: remoteServerConnectLocalHander
		"""
		return localToRemoteConnectManger.manager.get()
	
