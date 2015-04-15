#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import re
import urlparse
import time
import Queue
import logging
import sys
import traceback
from DDDProxy import hostParser
import thread
from remoteServer import DDDProxyConfig
from datetime import datetime
import threading
class domainConfig():
	defaultDomainList = ["google.com","gstatic.com","googleusercontent.com","googleapis.com","googleusercontent.com",
						"googlevideo.com","facebook.com","youtube.com","akamaihd.net","ytimg.com","twitter.com",
						"feedly.com","github.com","wikipedia.org","fbcdn.net","blogspot.com","t.co","ggpht.com",
						"twimg.com","facebook.net","blogger.com","flickr.com","gmail.com","stackoverflow.com",
						"gravatar.com","gmail.com","wikimedia.org","v2ex.com"]
	def __init__(self):
		self.domainList = {}
		try:
			fp = file(DDDProxyConfig.pacDomainConfig,"r")
			self.domainList = json.load(fp)
			fp.close()
		except:
			for domain in self.defaultDomainList:
				self.addDomain(domain)
	def save(self):
		fp = file(DDDProxyConfig.pacDomainConfig,"w")
		json.dump(self.domainList,fp)
		fp.close()

	def getDomainOpenedList(self):
		pacList = []
		domainList = self.getDomainListWithAnalysis()
		for domain in domainList:
			if domain["open"]:
				pacList.append(domain["domain"])
		return pacList
	def getDomainListWithAnalysis(self):
		data = [{"domain":key,"open":value["open"],"connectTimes":value["connectTimes"]} for (key,value) in self.domainList.items()]
		def sortDomainList(x,y):
			return x["connectTimes"]>y["connectTimes"];
		data.sort(cmp=lambda x,y : cmp(y["connectTimes"],x["connectTimes"]))
		return data;
	def removeDomain(self,domain):
		if domain in self.domainList:
			del self.domainList[domain]
			return True
		return False
	def closeDomain(self,domain):
		if domain in self.domainList:
			self.domainList[domain]["open"] = False
			return True
		return False
	def openDomain(self,domain):
		if domain in self.domainList:
			self.domainList[domain]["open"] = True
			return True
		return False
	def addDomain(self,domain,formGwflist = False):
		if not domain in self.domainList:
			self.domainList[domain] = {"connectTimes":0,"open":True,"formGwflist":formGwflist}
			return True
		return False
	def domainConnectTimes(self,domain,times):
		if domain in self.domainList:
			data = self.domainList[domain]
			data["connectTimes"] += times

class analysisSite(object):
	def __init__(self,domain,fromIp,timeMark):
		self.domain = domain
		self.fromIp = fromIp
		self.timeMark = timeMark
		self.incoming = 0
		self.outgoing = 0
		self.connect = 0
		self.lastTime = 0
		self.mergeTimes = 0
class analysisSiteList(object):
	def __init__(self):
		self.siteList = []
	def get(self,fromIp,domain,timeMark):
		try:
			url = urlparse.urlparse(domain)
			domain = url.netloc if len(url.netloc)>0 else domain
		except:
			pass
		
		domain = hostParser.getDomainName(domain)
		for s in self.siteList:
			if domain == s.domain and fromIp == s.fromIp and timeMark == s.timeMark:
				return s

		site = analysisSite(domain,fromIp,timeMark)
		self.siteList.append(site)
		return site
	
	def put(self,fromIp,domain,timeMark,type,val):
		site = self.get(fromIp,domain,timeMark)
		setattr(site, type, getattr(site, type)+val)
		site.lastTime = time.time()
		site.mergeTimes+=1
	def pop(self):
		minSite = None
		minTime = 0;
		current = time.time() - 10
		for s in self.siteList:
			if (minSite is None or minTime>s.lastTime) and s.lastTime < current:
				minSite = s
				minTime = s.lastTime
		if minSite:
			self.siteList.remove(minSite)
		return minSite;
config = domainConfig()

class autoDataObject(dict):
	def __getitem__(self, key):
		if key not in self:
			item = autoDataObject()
			self[key] = item
		else:
			item = dict.__getitem__(self, key)
		return item


class domainAnalysis():
	def __init__(self):
		self.domainAnalysisCache = analysisSiteList()
		self.domainAnalysis = autoDataObject()
		try:
			fp = file(DDDProxyConfig.domainAnalysisConfig,"r")
			data = json.load(fp,object_hook = autoDataObject)
			for k,v in data.items():
				self.domainAnalysis[int(k)] = v
			fp.close()
		except:
			pass
	def incrementData(self,addr, dataType, hostPort, message,length):
		timeMark = time.time();
		timeMark -= timeMark % 3600;
		self.domainAnalysisCache.put(addr,hostPort[0],int(timeMark),dataType, length)
	def getAnalysisData(self,selectDomain,startTime):
		startTime -= startTime%3600;
		index = 0
		outgoing = []
		incoming = []
		while True:
			timeData = self.domainAnalysis[startTime];
			outgoing.append(0)
			incoming.append(0)
			for formIp,domainData in timeData.items():
				for domain,data in domainData.items():
					if not selectDomain or domain == selectDomain:
						outgoing[index] += data["outgoing"]
						incoming[index] += data["incoming"]
			index+=1
			startTime+= 3600;
			if startTime > time.time():
				break
		return {"outgoing":outgoing,"incoming":incoming}
	def getTodayDomainAnalysis(self):
		todayTime = time.time()
		todayTime -= todayTime%86400
		todayTime += time.timezone
		domainCountData = {}
		for timeMark,timeData in self.domainAnalysis.items():
			if timeMark<todayTime:
				continue
			for formIp,domainData in timeData.items():
				for domain,data in domainData.items():
					if domain not in domainCountData:
						domainCountData[domain] = 0
					domainCountData[domain] += data["incoming"]+data["outgoing"]
		domainDataList = []
		countData = 0;
		for domain,data in domainCountData.items():
			countData += data
			domainDataList.append({"domain":domain,"dataCount":data})
		domainDataList.sort(cmp=lambda x,y : cmp(y["dataCount"],x["dataCount"]))
		return {"list":domainDataList,"countData":countData}
	@staticmethod
	def startAnalysis():
		thread.start_new_thread(analysis.analysisThread, tuple())
	def analysisThread(self):
		threading.currentThread().name = "analysisDataThread"
		while True:
			try:
				time.sleep(1)
				domainData = self.domainAnalysisCache.pop()
				if not domainData:
					continue
				
				if domainData.connect:
					config.domainConnectTimes(domainData.domain,domainData.connect)
				
				data = self.domainAnalysis[domainData.timeMark][domainData.fromIp][domainData.domain]
				if not "connect" in data:
					data["connect"] = 0
					data["incoming"] = 0
					data["outgoing"] = 0
				
				data["connect"] += domainData.connect
				data["incoming"] += domainData.incoming
				data["outgoing"] += domainData.outgoing
				
				
				dataExpireTime = time.time()-86400*7 #删除7天之前的数据
				for (k,d) in self.domainAnalysis.items():
					if(k < dataExpireTime):
						del self.domainAnalysis[k]
						break
				
				domainAnalysisJson = json.dumps(self.domainAnalysis)
				open(DDDProxyConfig.domainAnalysisConfig, "wt").write(domainAnalysisJson)
				"""use mysql on my office"""
	
			except:
				logging.error(("analysis error!", sys.exc_info(), traceback.format_exc()))
				pass

analysis = domainAnalysis()


if __name__ == "__main__":
	ll = autoDataObject()
	print ll

