# -*- coding: UTF-8 -*-
'''
Created on 2015年9月6日

@author: dxw
'''
from settingConfig import settingConfig
from remoteServerHandler import remoteServerConnect
from baseServer import baseServer
import math
import time



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
				self.connectName = "[remote:"+str(self.fileno())+"]	"+self.address[0]
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
		if self.count() < 5:
			host,port,auth = settingConfig.setting(settingConfig.remoteServerKey)
			if host and auth:
				try:
					c = remoteServerConnectLocalHander(self.server)
					c.connect((host,port),True)
					c.auth(auth)
					
					c.addAuthCallback(self.onConnectAuth)
					c.setConnectCloseCallBack(-1,self.onConnectClose)
					self.remoteConnectList.append(c)
				except:
					baseServer.log(3,host, port)
		return self.getConnectWithLoop();
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
	