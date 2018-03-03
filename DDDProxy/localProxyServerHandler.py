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
		self.proxyMode = False
		self.connectHost = ""
		self.preConnectRecvCache = b""
		self.httpMessageParse = httpMessageParser()
		self.socksMode = False
	def onRecv(self, data):
		self.preConnectRecvCache += data
		if not self.proxyMode:
			if data[0] == b'\x05' or data[0] == b'\x04':  # socks5
				if data[1] == b'\x02' or data[1] == b'\x01':
					self.setToProxyMode()
					self.socksMode = True
				else:
					log(1,"local >> ", len(data), binascii.b2a_hex(data))
					pass
			else:
				httpmessagedone = self.httpMessageParse.appendData(data)
				if self.httpMessageParse.headerOk() and httpmessagedone:
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
						self.proxyMode = False
					else:
						host = None
						port = None
						if path.find("status.dddproxy.com") > 0:
							jsonMessage = self.httpMessageParse.getBody()
							try:
								jsonBody = json.loads(jsonMessage)
							except:
								jsonBody = {"host":"","port":""}
							host = jsonBody["host"]
							port = jsonBody["port"]
						if self.setToProxyMode(host=host, port=port):
							self.connectHost = parserUrlAddrPort("https://" + path if method == "CONNECT" else path)[0]
							analysis.incrementData(self.address[0], domainAnalysisType.connect, self.connectHost, 1)
		
		if self.proxyMode:
			if not self.connectHost and self.socksMode and len(self.preConnectRecvCache) > 4:
				_d = self.preConnectRecvCache
				port = 0
				version = "Socks5"
				setConnectHost = False
				if(_d[0] == b"\x05"):
					if _d[3] == b'\x01':
						self.connectHost = "%d.%d.%d.%d" % (ord(_d[4]), ord(_d[5]), ord(_d[6]), ord(_d[7]))
						port = ord(_d[8]) * 0x100 + ord(_d[9])
						setConnectHost = True
					elif _d[3] == b"\x03":
						hostendindex = 5 + ord(_d[4])
						self.connectHost = _d[5:hostendindex]
						port = ord(_d[hostendindex]) * 0x100 + ord(_d[hostendindex + 1])
						setConnectHost = True
				elif _d[0] == b"\x04":
					if _d[1] == b'\x01' or _d[1] == b'\x02':
						self.connectHost = "%d.%d.%d.%d" % (ord(_d[4]), ord(_d[5]), ord(_d[6]), ord(_d[7]))
						version = "Socks4"
						if self.connectHost.startswith("0.0.0.") and ord(_d[7]) != 0:  # socks4a
							splits = _d[8:].split("\x00")
							self.connectHost = splits[-2]
							version = "Socks4a"
						setConnectHost = True
						port = ord(_d[2]) * 0x100 + ord(_d[3])
				else:
					log(3,_d[0],"not support")
					self.close()
				if setConnectHost:
					analysis.incrementData(self.address[0], domainAnalysisType.connect, self.connectHost, 1)
				self.connectName = self.symmetryConnectManager.filenoStr() + "	<	" + self.filenoStr() + "	" + version + ":" + self.connectHost + ":%d" % (port) 
				
			if self.preConnectRecvCache:
				if self.connectHost:
					analysis.incrementData(self.address[0], domainAnalysisType.incoming, self.connectHost, len(self.preConnectRecvCache))
				self.sendDataToSymmetryConnect(self.preConnectRecvCache)
				self.preConnectRecvCache = ""			
	def setToProxyMode(self, host=None, port=None):
		if self.proxyMode:
			return True
		self.proxyMode = True
		connect = localToRemoteConnectManger.getConnect()
		if host:
			try:
				connect = localToRemoteConnectManger.getConnectHost(host, port)
			except:
				pass
		if connect:
			connect.addLocalRealConnect(self)
			self.connectName = connect.filenoStr() + "	<	" + self.connectName
			return True
		else:
			self.close()
		return False
	def onSymmetryConnectData(self, data):
		self.send(data)
	def onSend(self, data):
		if self.connectHost:
			analysis.incrementData(self.address[0], domainAnalysisType.outgoing, self.connectHost, len(data))
		if not self.proxyMode and not self.getSendPending():
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
				respons["proxyAddr"] = parserUrlAddrPort(respons["pac"])
				respons["list"] = settingConfig.setting(settingConfig.remoteServerList)
				respons["version"] = version.version
			elif opt == "setServerList":
				settingConfig.setting(settingConfig.remoteServerList, postJson["data"])
				respons["status"] = "ok"
# 			elif opt == "testRemoteProxy":
# 				respons["status"] = ""
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
					host = url if getDomainName(url) else ""
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
		

