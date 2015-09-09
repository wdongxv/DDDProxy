# -*- coding: UTF-8 -*-
'''
Created on 2015年9月5日

@author: dxw
'''
from configFile import configFile


mainSetting = None
class settingConfig(configFile):
	
	remoteServerKey = "remoteServer"
	remoteServerList = "remoteServerList"
	def __init__(self):
		configFile.__init__(self)
		self.serverListLoop = 0
	
	def getConfigfileFilePath(self):
		return "/tmp/dddproxy_setting_config.json"

	def __getitem__(self, k):
		if k == settingConfig.remoteServerKey:
			serverList = self[settingConfig.remoteServerList]
			if serverList and len(serverList):
				if self.serverListLoop>=len(serverList):
					self.serverListLoop = 0;
				server = serverList[self.serverListLoop]
				self.serverListLoop+=1
				return (server["host"],int(server["port"]) if server["port"] else 8082,server["auth"])
			return (None,None,None)

		return configFile.__getitem__(self, k)
	
	@staticmethod
	def setting(key,value=None):
		global mainSetting
		if not mainSetting:
			mainSetting = settingConfig()
		if value:
			mainSetting[key] = value
		return mainSetting[key]