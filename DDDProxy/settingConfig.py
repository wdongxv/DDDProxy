# -*- coding: UTF-8 -*-
'''
Created on 2015年9月5日

@author: dxw
'''
from .configFile import configFile


mainSetting = None
class settingConfig(configFile):
	
# 	remoteServerKey = "remoteServer"
	remoteServerList = "remoteServerList"
	def __init__(self):
		configFile.__init__(self)
# 		self.serverListLoop = 0
	
	def getConfigfileFilePath(self):
		return configFile.makeConfigFilePathName("setting.json")

	@staticmethod
	def setting(key,value=None):
		global mainSetting
		if not mainSetting:
			mainSetting = settingConfig()
		if value:
			mainSetting[key] = value
		return mainSetting[key]