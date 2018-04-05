# -*- coding: UTF-8 -*-
'''
Created on 2015年9月6日

@author: dxw
'''
import random
import time

from .configFile import configFile
from . import log
from .settingConfig import settingConfig
from .symmetryConnectServerHandler import symmetryConnectServerHandler
from .fakeSymmetryConnectServerHandler import fakeSymmetryConnectServerHandler
from . import domainConfig
from .hostParser import getDomainName

class localToRemoteConnecter(symmetryConnectServerHandler):

	def __init__(self, server, authCode, *args, **kwargs):
		symmetryConnectServerHandler.__init__(self, server, authCode, *args, **kwargs)

	def addLocalRealConnect(self, connect):
		self.addSymmetryConnect(connect, self.makeSymmetryConnectId())

	def onClose(self):
		symmetryConnectServerHandler.onClose(self)
		localToRemoteConnectManger.manager.onConnectClose(self)

	def SSLLocalCertPath(self, remoteServerHost, remoteServerPort):
		return configFile.makeConfigFilePathName("%s-%d.pem" % (remoteServerHost, remoteServerPort))


class localToRemoteConnectManger():

	def __init__(self, server, maxConnectByOnServer=2):
		"""
		@param server: _baseServer
		"""
		self.server = server;
		self.remoteConnectList = []
		self.server.addDelay(1, self.handlerRemoteConnects)
		self.maxConnectByOnServer = maxConnectByOnServer
		self.fakeProxyServer = fakeSymmetryConnectServerHandler(self.server)
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
			log.log(3, "remoteServerList not set !!!")
			return None
		
		remoteServer = random.choice(remoteServerList)
		remoteConnect = localToRemoteConnecter(self.server, remoteServer["auth"])
		port = int(remoteServer["port"]) if remoteServer["port"] else 8083
		remoteConnect.connect((remoteServer["host"], port))
		self.remoteConnectList.append(remoteConnect);
		return remoteConnect

	def handlerRemoteConnects(self):
		remoteServerList = settingConfig.setting(settingConfig.remoteServerList)
		if remoteServerList != None:
			removeConnectList = []
			for remoteConnect in self.remoteConnectList:
				requestRemove = True
				for remoteServer in remoteServerList:
					port = int(remoteServer["port"]) if remoteServer["port"] else 8083
					if(remoteServer['host'] == remoteConnect.address[0] and port == remoteConnect.address[1]):
						requestRemove = False
						break
				if requestRemove:
					remoteConnect.info["status"] = "remove"
				if (not remoteConnect.connectStatus()) or requestRemove or remoteConnect.slowConnectStatus:
					removeConnectList.append(remoteConnect)
			for remoteConnect in removeConnectList:
				self.remoteConnectList.remove(remoteConnect)
				remoteConnect.requestIdleClose();
			
			for _ in range(self.maxConnectByOnServer):
				if self.maxConnectByOnServer > len(self.remoteConnectList):
					self.addRemoteConnect()
		self.server.addDelay(30, self.handlerRemoteConnects)
		
	def onConnectClose(self, connect):
		if connect in self.remoteConnectList:
			self.remoteConnectList.remove(connect)

	manager = None

	@staticmethod
	def install(server, maxConnectByOnServer=2):
		if not localToRemoteConnectManger.manager:
			localToRemoteConnectManger.manager = localToRemoteConnectManger(server, maxConnectByOnServer)

	@staticmethod
	def getConnectByHost(host, port=None):
		port = port if port else 8083
		for connet in localToRemoteConnectManger.manager.remoteConnectList:
			if connet.address[0] == host and connet.address[1] == port:
				return connet
		return None
	
	@staticmethod
	def getConnect(domain=None):
		"""
		@return: remoteServerConnectLocalHander
		"""
		
		if domain:
			status = domainConfig.config.domainSettingStatus(domain)
			topDomain = getDomainName(domain)
			status = domainConfig.config.domainSettingStatus(topDomain) if ( topDomain != None and status == None ) else status
			if status != "proxy":
				return localToRemoteConnectManger.manager.fakeProxyServer
			
		return localToRemoteConnectManger.manager.get()
	
