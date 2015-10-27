#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
from os.path import dirname

from DDDProxy.domainAnalysis import analysis, domainAnalysisType
from DDDProxy.hostParser import parserUrlAddrPort, getDomainName
from baseServer import sockConnect
import domainConfig
from remoteConnectManger import remoteConnectManger
from remoteServerHandler import remoteServerConnect
from settingConfig import settingConfig
from socetMessageParser import httpMessageParser
import time
from email import mime
from DDDProxy.baseServer import get_mime_type

class localProxyServerConnectHandler(sockConnect):
	"""
	@type remoteConnect: remoteServerConnect
	"""
	def __init__(self, *args, **kwargs):
		sockConnect.__init__(self, *args, **kwargs)
		self.messageParse = httpMessageParser()
		self.mode = ""
		self.remoteConnect = None
		self.recvCache = ""
		
		self.connectHost = ""
	def onClose(self):
		if(self.remoteConnect):
			self.remoteConnect.sendOpt(self.fileno(), remoteServerConnect.optCloseConnect)
			self.remoteConnect.removeAllCallback(self.fileno())
		sockConnect.onClose(self)
	def onRecv(self, data):
		sockConnect.onRecv(self, data)
		self.recvCache += data
		if self.mode == "proxy":
			if self.remoteConnect and self.recvCache:
				if self.connectHost:
					analysis.incrementData(self.address[0], domainAnalysisType.incoming, self.connectHost, len(self.recvCache))
				self.remoteConnect.sendData(self.fileno(), self.recvCache)
				self.recvCache = ""
			return
		if self.messageParse.appendData(data):
			method = self.messageParse.method()
			path = self.messageParse.path()
			self.connectName = self.filenoStr() + "	" + method + "	" + path
			if not path.startswith("http://") and method in ["GET", "POST"]:
				path = path.split("?")
				self.onHTTP(self.messageParse.headers,
						method,
						path[0],
						path[1] if len(path) > 1 else "",
						self.messageParse.getBody() if method == "POST" else "")
				self.mode = "http"
			else:
				
				self.mode = "proxy"
				
				connect = None
				if path.find("status.dddproxy.com")>0:
					try:
						jsonMessage = self.messageParse.getBody()
						jsonBody = json.loads(jsonMessage)
						connectList = remoteConnectManger.getConnectHost(jsonBody["host"],jsonBody["port"])
						if connectList:
							for _,v in connectList.items():
								connect = v
					except:
						pass
# 				else:
				if not connect:
					connect = remoteConnectManger.getConnect()
				
				if connect:
					connect.addAuthCallback(self.onRemoteConnectAuth)
					connect.setConnectCloseCallBack(self.fileno(), self.onRemoteConnectClose)
				else:
					self.close()
				
				self.connectHost = parserUrlAddrPort("https://" + path if method == "CONNECT" else path)[0]
				analysis.incrementData(self.address[0], domainAnalysisType.connect, self.connectHost, 1)
		else:
			pass
# 	def onRemoteConnectRecv(self,connect,data):
# 		self.send(data)
	def onRemoteConnectClose(self, connect):
		self.close()
	def onRemoteConnectAuth(self, connect):
		"""
		@type connect: remoteServerConnectLocalHander
		"""
		connect.setRecvCallback(self.fileno(), self.send)
		self.remoteConnect = connect
		self.onRecv("");
		self.connectName = connect.filenoStr() + "	<	" + self.connectName
	def onSend(self, data):
		sockConnect.onSend(self, data)
		if self.connectHost:
			analysis.incrementData(self.address[0], domainAnalysisType.outgoing, self.connectHost, len(data))
		if self.mode == "http" and len(self.dataSendList) == 0:
			if self.messageParse.connection() != "keep-alive":
				self.close()
			else:
				self.messageParse.clear()
	
	def getFileContent(self, name):
		content = None
		try:
			f = dirname(__file__) + "/template" + name
			f = open(f)
			content = f.read()
			f.close()
		except:
			pass
		return content
	
	def onHTTP(self, header, method, path, query, post):
# 		log.log(1,self,header,method,path,query,post)
		if method == "POST":
			postJson = json.loads(post)
			opt = postJson["opt"]
			respons = {}

			if(opt == "status"):
				respons = self.server.dumpConnects()
			elif(opt == "serverList"):
				respons["pac"] = "http://" + self.messageParse.getHeader("host") + "/pac"
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
			self.reseponse(respons,connection=self.messageParse.connection())
		elif path == "/pac":
			content = self.getFileContent("/pac.js")
			domainList = domainConfig.config.getDomainOpenedList()
			domainListJs = ""
			for domain in domainList:
				domainListJs += "A(\"" + domain + "\")||"
			content = content.replace("{{domainList}}", domainListJs)
			content = content.replace("{{proxy_ddr}}", self.messageParse.getHeader("host"))
			self.reseponse(content,connection=self.messageParse.connection())
		else:
			if path == "/":
				path = "/index.html"
			content = self.getFileContent(path)
			if content:
				
				self.reseponse(content,ContentType=get_mime_type(path),connection=self.messageParse.connection())
			else:
				self.reseponse("\"" + path + "\" not found", code=404,connection=self.messageParse.connection())
		

