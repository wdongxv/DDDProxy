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
import threading
import time

from .baseServer import sockConnect
from .configFile import configFile
from . import log
from .settingConfig import settingConfig
from .symmetryConnectServerHandler import symmetryConnect
from .symmetryConnectServerHandler import symmetryConnectServerHandler

maxConnectByOnServer = 2
remoteConnectMaxTime = 0
	
class remoteServerConnecter(symmetryConnectServerHandler):
	def __init__(self, server, authCode, *args, **kwargs):
		symmetryConnectServerHandler.__init__(self, server,authCode, *args, **kwargs)
	def addLocalRealConnect(self, connect):
		self.addSymmetryConnect(connect, self.makeSymmetryConnectId())
	def onClose(self):
		symmetryConnectServerHandler.onClose(self)
		localToRemoteConnectManger.manager.onConnectClose(self)
	def requestIdleClose(self):
		if self in localToRemoteConnectManger.manager.remoteConnectList:
			return
		symmetryConnectServerHandler.requestIdleClose(self)
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
			log.log(3,"remoteServerList not set !!!")
			return None
		
		remoteServer = random.choice(remoteServerList)
		remoteConnect = remoteServerConnecter(self.server, remoteServer["auth"])
		port = int(remoteServer["port"]) if remoteServer["port"] else 8083
		remoteConnect.connect((remoteServer["host"], port))
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
				port = int(remoteServer["port"]) if remoteServer["port"] else 8083
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
		port = port if port else 8083
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
	
