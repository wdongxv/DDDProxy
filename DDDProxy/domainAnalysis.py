# -*- coding: UTF-8 -*-
'''
Created on 2015年9月9日

@author: dxw
'''
import urlparse
import re
import time
import json
import thread
import domainConfig
import threading
from configFile import autoDataObject
from baseServer import baseServer


def getDomainName(host):
	hostMatch = re.compile('^(.*?)\.*([^\.]+)(\.(?:net\.cn|com\.cn|com\.hk|co\.jp|org\.cn|[^\.\d]{2,3}))$')
	match = hostMatch.match(host)
	if match:
		hostGroup = match.groups()
		if len(hostGroup) > 2:
			host = "%s%s" % (hostGroup[1], hostGroup[2])
	return host
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
		
		domain = getDomainName(domain)
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
domainAnalysisConfig = "/tmp/domainAnalysisConfig.json"
class domainAnalysisType:
	connect = "connect"
	incoming = "incoming"
	outgoing = "outgoing"
	

class domainAnalysis():
	def __init__(self):
		self.domainAnalysisCache = analysisSiteList()
		self.domainAnalysis = autoDataObject()
		try:
			fp = file(domainAnalysisConfig,"r")
			data = json.load(fp,object_hook = autoDataObject)
			for k,v in data.items():
				self.domainAnalysis[int(k)] = v
			fp.close()
		except:
			pass
	def incrementData(self,addr, dataType, host, length):
		"""
		@param dataType: domainAnalysisType
		"""
		timeMark = time.time();
		timeMark -= timeMark % 3600;
		self.domainAnalysisCache.put(addr,host,int(timeMark),dataType, length)
	def getAnalysisData(self,selectDomain,startTime,todayStartTime):
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
						outgoing[index] += data[domainAnalysisType.outgoing]
						incoming[index] += data[domainAnalysisType.incoming]
			index+=1
			startTime += 3600;
			if startTime > time.time():
				break
			
		domainCountData = {}
		for timeMark,timeData in self.domainAnalysis.items():
			if timeMark<todayStartTime:
				continue
			for formIp,domainData in timeData.items():
				for domain,data in domainData.items():
					if domain not in domainCountData:
						domainCountData[domain] = 0
					domainCountData[domain] += data[domainAnalysisType.incoming]+data[domainAnalysisType.outgoing]
		domainDataList = []
		countData = 0;
		for domain,data in domainCountData.items():
			countData += data
			domainDataList.append({"domain":domain,"dataCount":data})
		domainDataList.sort(cmp=lambda x,y : cmp(y["dataCount"],x["dataCount"]))
		return {"outgoing":outgoing,"incoming":incoming,"domainDataList":domainDataList,"countData":countData}

	@staticmethod
	def startAnalysis(server):
		"""
		@param server: baseServer
		"""
		server.addDelay(5, analysis.analysisThread,server)
# 		mainThreadPool.callInThread(analysis.analysisThread)
# 		thread.start_new_thread(analysis.analysisThread, tuple())
	def analysisThread(self,server):
		try:
			domainData = self.domainAnalysisCache.pop()
			if domainData:
				if domainData.connect:
					domainConfig.config.domainConnectTimes(domainData.domain,domainData.connect)
				
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
				open(domainAnalysisConfig, "wt").write(domainAnalysisJson)

		except:
			baseServer.log(3,"analysis error!")
		server.addDelay(5, analysis.analysisThread,server)
		
analysis = domainAnalysis()