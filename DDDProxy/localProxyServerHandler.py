#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from os.path import dirname

from domainAnalysis import analysis, domainAnalysisType
import domainConfig
from hostParser import parserUrlAddrPort, getDomainName
from localToRemoteConnectManger import localSymmetryConnect
from localToRemoteConnectManger import localToRemoteConnectManger
from mime import get_mime_type
from settingConfig import settingConfig
from socetMessageParser import httpMessageParser


class localConnectHandler(localSymmetryConnect):
	def __init__(self, *args, **kwargs):
		localSymmetryConnect.__init__(self, *args, **kwargs)
		self.mode = ""
		self.connectHost = ""

		self.preConnectRecvCache = ""

		self.httpMessageParse = httpMessageParser()
		
	def onRecv(self, data):

		self.preConnectRecvCache += data
		if self.mode == "proxy":
			if self.serverAuthPass and self.preConnectRecvCache:

				if self.connectHost:
					analysis.incrementData(self.address[0], domainAnalysisType.incoming, self.connectHost, len(self.preConnectRecvCache))
					
				self.sendDataToSymmetryConnect(self.preConnectRecvCache)
				self.preConnectRecvCache = ""
			return
		if self.httpMessageParse.appendData(data):
			method = self.httpMessageParse.method()
			path = self.httpMessageParse.path()
			self.connectName = self.filenoStr() + "	" + method + "	" + path
			if not path.startswith("http://") and method in ["GET", "POST"]:
				path = path.split("?")
				self.onHTTP(self.httpMessageParse.headers,
						method,
						path[0],
						path[1] if len(path) > 1 else "",
						self.httpMessageParse.getBody() if method == "POST" else "")
				self.mode = "http"
			else:
				
				self.mode = "proxy"
				
				connect = localToRemoteConnectManger.getConnect()
				
				if path.find("status.dddproxy.com")>0:
					try:
						connect = None
						jsonMessage = self.httpMessageParse.getBody()
						jsonBody = json.loads(jsonMessage)
						connectList = localToRemoteConnectManger.getConnectHost(jsonBody["host"],jsonBody["port"])
						if connectList:
							for _,v in connectList.items():
								connect = v
					except:
						pass
				
				if connect:
					connect.addLocalRealConnect(self)
				else:
					self.close()
				
				self.connectHost = parserUrlAddrPort("https://" + path if method == "CONNECT" else path)[0]
				analysis.incrementData(self.address[0], domainAnalysisType.connect, self.connectHost, 1)
		else:
			pass
	def onSymmetryConnectData(self,data):
		self.send(data)
	def onServerAuthPass(self):
		localSymmetryConnect.onServerAuthPass(self)
		"""
		@type connect: remoteServerConnectLocalHander
		"""
		self.connectName = self.symmetryConnectManager.filenoStr() + "	<	" + self.connectName
		self.onRecv("");
		
	def onSend(self, data):
		if self.connectHost:
			analysis.incrementData(self.address[0], domainAnalysisType.outgoing, self.connectHost, len(data))
		if self.mode == "http" and not self.getSendPending():
			if self.httpMessageParse.connection() != "keep-alive":
				self.close()
			else:
				self.httpMessageParse.clear()
	
	
	def onHTTP(self, header, method, path, query, post):
# 		log.log(1,self,header,method,path,query,post)
		if method == "POST":
			postJson = json.loads(post)
			opt = postJson["opt"]
			respons = {}

			if(opt == "status"):
				respons = self.server.dumpConnects()
			elif(opt == "serverList"):
				respons["pac"] = "http://" + self.httpMessageParse.getHeader("host") + "/pac"
				respons["list"] = settingConfig.setting(settingConfig.remoteServerList)
			elif opt == "setServerList":
				settingConfig.setting(settingConfig.remoteServerList, postJson["data"])
				respons["status"] = "ok"
# 			elif opt == "testRemoteProxy":
# 				respons["status"] = ""
			elif opt == "domainList":
				
				if "action" in postJson:
					action = postJson["action"]
					domain = postJson["domain"]
					respons={"status":"ok"}
					if action == "delete":
						domainConfig.config.removeDomain(domain)
					elif action == "open":
						domainConfig.config.openDomain(domain)
					elif action == "close":
						domainConfig.config.closeDomain(domain)
					else:
						respons={"status":"no found action"}
				else:
					respons["domainList"] = domainConfig.config.getDomainListWithAnalysis()
			elif opt == "analysisData":
				respons["analysisData"] = analysis.getAnalysisData(
																selectDomain=postJson["domain"],
																startTime=postJson["startTime"],
																todayStartTime=postJson["todayStartTime"]
																)
			elif opt == "addDomain":
				url = postJson["url"]
				host = parserUrlAddrPort(url)[0]
				if host:
					host = getDomainName(host)
				else:
					host = url if getDomainName(url) else ""
				respons["status"] = "ok" if domainConfig.config.addDomain(host) else "error"
			self.reseponse(respons,connection=self.httpMessageParse.connection())
		elif path == "/pac":
			content = self.getFileContent(dirname(__file__) + "/template/pac.js")
			domainList = domainConfig.config.getDomainOpenedList()
			domainListJs = ""
			for domain in domainList:
				domainListJs += "A(\"" + domain + "\")||"
			content = content.replace("{{domainList}}", domainListJs)
			content = content.replace("{{proxy_ddr}}", self.httpMessageParse.getHeader("host"))
			self.reseponse(content,connection=self.httpMessageParse.connection())
		else:
			if path == "/":
				path = "/index.html"
			content = self.getFileContent(dirname(__file__) + "/template" +path)
			if content:
				
				self.reseponse(content,ContentType=get_mime_type(path),connection=self.httpMessageParse.connection())
			else:
				self.reseponse("\"" + path + "\" not found", code=404,connection=self.httpMessageParse.connection())
		

