# -*- coding: UTF-8 -*-
'''
Created on 2015年9月8日

@author: dxw
'''
from .configFile import configFile
import time
from .hostParser import getDomainName
from functools import cmp_to_key
from .log import cmp

GFWListKeyName = "GFW List"
class domainConfig(configFile):

	def __init__(self):
		configFile.__init__(self)

	def getConfigfileFilePath(self):
		return configFile.makeConfigFilePathName("pacDomainConfig.json")

	def getDomainList(self, opend=1):
		"""
		0 close
		1 open 
		2 all
		"""
		pacList = []
		domainList = self.getDomainListWithAnalysis()
		for domain in domainList:
			if domain["domain"] == GFWListKeyName:
				continue
			if opend == 2 or domain["open"] == opend:
				pacList.append(domain["domain"])
		if opend == 1:
			pacList.extend(self.getGFWDomainList())
		return pacList

	def getDomainListWithAnalysis(self):
		data = [{"domain":key, "open":value["open"], "connectTimes":value["connectTimes"]} for (key, value) in self.setting.items()]

		def sort(x, y):
			o = cmp(y["open"], x["open"])
			return cmp(y["connectTimes"], x["connectTimes"]) if o == 0 else o

		return sorted(data, key=cmp_to_key(sort));

	def removeDomain(self, domain):
		if domain in self.setting:
			del self.setting[domain]
			self.save()
			return True
		return False

	def closeDomain(self, domain):
		return self.addDomain(domain, False)

	def openDomain(self, domain):
		return self.addDomain(domain, True)

	def addDomain(self, domain, Open=True, updateTime=0):
		if domain:
			if not domain in self.setting:
				self.setting[domain] = {"connectTimes":0, "open":Open,
									"update":time.time(), "createTime":time.time()}
			else:
				currentDomain = self.setting[domain];
				if updateTime and "update" in currentDomain:
					if updateTime <= currentDomain["update"]:
						return False
				currentDomain["open"] = Open
				currentDomain["update"] = time.time()
		else:
			return False
		self.save()
		return True
	def getGFWDomainList(self):
		if GFWListKeyName in self.setting:
			_GFWList = self.setting[GFWListKeyName]
			if _GFWList["open"] == 1:
				return _GFWList["domainList"]
		return []
	def resetGFWListDomain(self):
		if GFWListKeyName in self.setting:
			del self.setting[GFWListKeyName]
		
	def addGFWListDomain(self, domain):
		if not GFWListKeyName in self.setting:
			self[GFWListKeyName] = {"open":1, "update":time.time(), "connectTimes":0, "createTime":time.time(),"domainList":[]}
		self[GFWListKeyName]["domainList"].append(domain)
	def domainConnectTimes(self, domain, times):
		if domain in self.setting:
			data = self.setting[domain]
			data["connectTimes"] += times
			self.save()
		else:
			_domain = getDomainName(domain)
			if _domain and not _domain == domain:
				self.domainConnectTimes(_domain, times)


config = domainConfig()
