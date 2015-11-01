# -*- coding: UTF-8 -*-
'''
Created on 2015年9月6日

@author: dxw
'''
from settingConfig import settingConfig
from remoteServerHandler import remoteServerConnect
import math
import time
from DDDProxy.remoteServerHandler import remoteServerHandler



class remoteServerConnectLocalHander(remoteServerConnect):
	def __init__(self, server, *args, **kwargs):
		remoteServerConnect.__init__(self, server, *args, **kwargs)
		self.authCallbackList = []
		self.authPass = False
		
	def onOpt(self, connectId, opt):
		if connectId == remoteServerHandler.serverToServerAuthConnectId:
			if opt == remoteServerConnect.optAuthOK:
				for cb in self.authCallbackList:
					self.server.addCallback(cb,connect=self)
				self.authCallbackList = []
				self.authPass = True
				self.connectName = "[remote:"+str(self.fileno())+"]	"+self.address[0]
				
				self.setServerPing(True)
			elif opt == remoteServerConnect.optAuthError:
				self.close()
# 		elif opt == remoteServerConnect.optCloseConnect:
# 			self.close()
		else:
			remoteServerConnect.onOpt(self,connectId,opt)
# 		log.log(2,"onOpt",connectId,opt)
	def auth(self,auth):
		randomNum = math.floor(time.time())
		self.sendData(remoteServerHandler.serverToServerAuthConnectId,self.authMake(auth, randomNum))
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
		self.remoteConnectList = {}
		self.remoteConnectListLoop = 0
	def get(self):
		"""
		@return: remoteServerConnectLocalHander
		"""
		maxCount = 2
		self.remoteConnectListLoop += 1;
		remoteServerList = settingConfig.setting(settingConfig.remoteServerList)
		if self.remoteConnectListLoop >= len(remoteServerList)*maxCount:
			self.remoteConnectListLoop = 0
		i = 0
		for remoteServer in remoteServerList:
			connectList = None
			port = int(remoteServer["port"]) if remoteServer["port"] else 8082
			remoteServerKey = remoteServer["host"]+":"+str(port)
			if remoteServerKey in self.remoteConnectList:
				connectList = self.remoteConnectList[remoteServerKey]
			else:
				self.remoteConnectList[remoteServerKey] = connectList = {}
				
			if  self.remoteConnectListLoop >= i and self.remoteConnectListLoop < i + maxCount:
				index = self.remoteConnectListLoop-i
				connect = None
				if index in connectList:
					connect = connectList[index]
				else:
					connect = remoteServerConnectLocalHander(self.server)
					connect.connect((remoteServer["host"],port),True)
					connect.auth(remoteServer["auth"])
					connect.setConnectCloseCallBack(-1,self.onConnectClose)
					connectList[index] = connect
				return connect
			i += maxCount
		return None
	def onConnectClose(self,connect):
		for _,connectList in self.remoteConnectList.items():
			for k,v in connectList.items():
				if v == connect:
					del connectList[k]
					return

	manager = None
	@staticmethod
	def install(server):
		if not remoteConnectManger.manager:
			remoteConnectManger.manager = remoteConnectManger(server)
	@staticmethod
	def getConnectHost(host,port):
		port = port if str(port) else "8082"
		return remoteConnectManger.manager.remoteConnectList[host+":"+port]
		
	@staticmethod
	def getConnect():
		"""
		@return: remoteServerConnectLocalHander
		"""
		return remoteConnectManger.manager.get()
	