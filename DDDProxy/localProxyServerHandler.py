#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from os.path import dirname

from .domainAnalysis import analysis, domainAnalysisType
from . import domainConfig
from .hostParser import parserUrlAddrPort, getDomainName
from .localToRemoteConnectManger import localToRemoteConnectManger
from .mime import get_mime_type
from .settingConfig import settingConfig
from .socetMessageParser import httpMessageParser
from .symmetryConnectServerHandler import symmetryConnect
from . import version
import binascii
from .log import log


class localConnectHandler(symmetryConnect):
	def __init__(self, *args, **kwargs):
		symmetryConnect.__init__(self, *args, **kwargs)
		self.proxyStatusMode = None

		self.connectHost = ""
		self.connectPort = 0
		self.connectMethod = ""
		self.connectHttpPath = None
		
		self.preConnectRecvCache = b""
		self.httpMessageParse = None
	def __str__(self, *args, **kwargs):
		if self.connectHost or self.connectHttpPath:
			name = ""
			if self.symmetryConnectManager:
				name += self.symmetryConnectManager.filenoStr() + "	<	"
			name +=  self.filenoStr() + "	" + self.connectMethod + " "
			if self.connectHttpPath:
				name += self.connectHttpPath
			else:
				name += self.connectHost + ":%d" % (self.connectPort) 
			return name
		return symmetryConnect.__str__(self, *args, **kwargs)

	def onRecv(self, data):
		self.preConnectRecvCache += data
		if self.proxyStatusMode != "proxy":
			_d = self.preConnectRecvCache
			if  (_d[0] == 5 or _d[0] == 4 ): # socks x
				if (_d[1] == 2 or _d[1] == 1): 
					if len(_d) <= 4:
						self.preConnectRecvCache = self.preConnectRecvCache[3:]
						return self.send(b"\x05\x00")
					port = 0
					version = "Socks5"
					if(_d[0] == 5):
						if _d[3] ==1:
							self.connectHost = "%d.%d.%d.%d" % (_d[4], _d[5], _d[6], _d[7])
							port = _d[8] * 0x100 + _d[9]
						elif _d[3] ==3:
							hostendindex = 5 + _d[4]
							self.connectHost = _d[5:hostendindex].decode()
							port = _d[hostendindex] * 0x100 + _d[hostendindex + 1]
					elif _d[0] == 4:
						if _d[1] == 1 or _d[1] == 2:
							self.connectHost = "%d.%d.%d.%d" % (_d[4], _d[5], _d[6], _d[7])
							version = "Socks4"
							if self.connectHost.startswith("0.0.0.") and _d[7] != 0:  # socks4a
								splits = _d[8:].split(b"\x00")
								self.connectHost = splits[-2].decode()
								version = "Socks4a"
							port = _d[2] * 0x100 + _d[3]
					if self.connectHost:
						analysis.incrementData(self.address[0], domainAnalysisType.connect, self.connectHost, 1)
						self.proxyStatusMode = "proxy"
						self.installRemoteConnect()
					self.connectMethod = version
					self.connectPort = port
					log(1, self, " = socksMode")
				else:
					log(2,"unknow ", len(data), binascii.b2a_hex(data))
					self.close()
			else:
				if not self.httpMessageParse:
					self.httpMessageParse = httpMessageParser()
				httpmessagedone = self.httpMessageParse.appendData(data)
				if self.httpMessageParse.headerOk() and httpmessagedone:
					self.connectMethod = self.httpMessageParse.method()
					path = self.httpMessageParse.path()
					if path.startswith("/"):
						self.connectHttpPath = path
						path = path.split("?")
						self.proxyStatusMode = "http"
						self.onHTTP(self.httpMessageParse.headers,
								self.connectMethod,
								path[0],
								path[1] if len(path) > 1 else "",
								self.httpMessageParse.getBody() if self.connectMethod == "POST" else "")
					else:
						remoteHost = None
						if path.find("status.dddproxy.com") > 0:
							jsonMessage = self.httpMessageParse.getBody()
							try:
								jsonBody = json.loads(jsonMessage)
							except:
								jsonBody = {"host":"","port":""}
							remoteHost = (jsonBody["host"],jsonBody["port"])
						self.connectHost,self.connectPort = parserUrlAddrPort("https://" + path if self.connectMethod == "CONNECT" else path)
						if self.connectMethod != "CONNECT":
							self.connectHttpPath = path
						self.proxyStatusMode = "proxy"
						if self.installRemoteConnect(remoteHost=remoteHost):
							analysis.incrementData(self.address[0], domainAnalysisType.connect, self.connectHost, 1)
							pass
		if self.proxyStatusMode == "proxy":
			if self.preConnectRecvCache:
				if self.connectHost:
					analysis.incrementData(self.address[0], domainAnalysisType.incoming, self.connectHost, len(self.preConnectRecvCache))
				self.sendDataToSymmetryConnect(self.preConnectRecvCache)
				self.preConnectRecvCache = b""			
	def installRemoteConnect(self, remoteHost=None):
		if self.symmetryConnectManager:
			return True;
		if remoteHost:
			remote = localToRemoteConnectManger.getConnectByHost(remoteHost[0],remoteHost[1])
		else:
			remote = localToRemoteConnectManger.getConnect(self.connectHost)
		if remote:
			remote.addLocalRealConnect(self)
			self.symmetryConnectManager = remote
			return True
		else:
			self.close()
		return False
	def onSymmetryConnectData(self, data):
		self.send(data)
	def onSend(self, data):
		if self.connectHost:
			analysis.incrementData(self.address[0], domainAnalysisType.outgoing, self.connectHost, len(data))
		if self.proxyStatusMode == "http" and not self.getSendPending():
			if self.httpMessageParse.connection() != "keep-alive":
				self.close()
			else:
				self.httpMessageParse.clear()
	
	
	def onHTTP(self, header, method, path, query, post):
# 		log.log(1,self,header,method,path,query,post)
		if method == "POST":
			try:
				postJson = json.loads(post.decode())
			except:
				return self.reseponse({"err":"bad request"}, code=404, connection=self.httpMessageParse.connection())
			opt = postJson["opt"]
			respons = {}

			if(opt == "status"):
				respons = self.server.dumpConnects()
			elif(opt == "serverList"):
				respons["pac"] = "http://" + self.httpMessageParse.getHeader("host") + "/pac"
				respons["proxyAddr"] = parserUrlAddrPort(respons["pac"])
				respons["list"] = settingConfig.setting(settingConfig.remoteServerList)
				respons["version"] = version.version
			elif opt == "setServerList":
				settingConfig.setting(settingConfig.remoteServerList, postJson["data"])
				respons["status"] = "ok"
			elif opt == "domainList":
				if "action" in postJson:
					action = postJson["action"]
					domain = postJson["domain"]
					respons = {"status":"ok"}
					if action == "delete":
						domainConfig.config.removeDomain(domain)
					elif action == "open":
						domainConfig.config.openDomain(domain)
					elif action == "close":
						domainConfig.config.closeDomain(domain)
					else:
						respons = {"status":"no found action"}
				else:
					respons["domainList"] = domainConfig.config.getDomainListWithAnalysis()
			elif opt == "analysisData":
				respons["analysisData"] = analysis.getAnalysisData(
																selectDomain=postJson["domain"],
																startTime=postJson["startTime"],
																todayStartTime=postJson["todayStartTime"]
																)
			elif opt == "restore":
				if postJson["clearAll"]:
					domainConfig.config.setting = {}
				domainList = postJson["domainList"]
				for domain in domainList:
					domainConfig.config.addDomain(domain[0], Open=domain[1],
												updateTime=domain[2] if len(domain) > 2 else 0)
				respons["status"] = "ok"
			elif opt == "addDomain":
				url = postJson["url"]
				host = parserUrlAddrPort(url)[0]
				if host:
					host = getDomainName(host)
				else:
					host = url 
				respons["status"] = "ok" if domainConfig.config.addDomain(host) else "error"
			self.reseponse(respons, connection=self.httpMessageParse.connection())
		elif path == "/pac":
			content = self.getFileContent(dirname(__file__) + "/template/pac.js")
			content = content.replace("{{domainWhiteListJson}}", json.dumps(domainConfig.config.getDomainList(0)))
			content = content.replace("{{domainListJson}}", json.dumps(domainConfig.config.getDomainList(1)))
			content = content.replace("{{proxy_ddr}}", self.httpMessageParse.getHeader("host"))
			self.reseponse(content, connection=self.httpMessageParse.connection())
			
		else:
			if path == "/":
				path = "/index.html"
			content = self.getFileContent(dirname(__file__) + "/template" + path)
			if content and path.find("..") == -1:
				self.reseponse(content, ContentType=get_mime_type(path), connection=self.httpMessageParse.connection())
			else:
				self.reseponse("\"" + path + "\" not found", code=404, connection=self.httpMessageParse.connection())
		

