#!/usr/bin/env python
# -*- coding: utf-8 -*-


from baseServer import sockConnect
from socetMessageParser import httpMessageParser
import httplib
from baseServer import baseServer
from os.path import dirname
import json
from settingConfig import settingConfig
import domainConfig
from datetime import datetime
from remoteConnectManger import remoteConnectManger
from remoteServerHandler import remoteServerConnect

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
	def onClose(self):
		if(self.remoteConnect):
			self.remoteConnect.sendOpt(self.fileno(),remoteServerConnect.optCloseConnect)
			self.remoteConnect.removeAllCallback(self.fileno())
		sockConnect.onClose(self)
	def onRecv(self, data):
		sockConnect.onRecv(self, data)
		
		self.recvCache += data
		if self.mode == "proxy":
			if self.remoteConnect and self.recvCache:
				self.remoteConnect.sendData(self.fileno(),self.recvCache)
				self.recvCache = ""
			return
		if self.messageParse.appendData(data):
			method = self.messageParse.method()
			path = self.messageParse.path()
			self.connectName = method+" "+path
			if not path.startswith("http://") and method in ["GET","POST"]:
				path = path.split("?")
				self.onHTTP(self.messageParse.headers,
						method,
						path[0],
						path[1] if len(path)>1 else "",
						self.messageParse.getBody() if method == "POST" else "")
				self.mode = "http"
			else:
				self.mode = "proxy"
				baseServer.log(1,self,"proxy mode",method,path)
				connect = remoteConnectManger.getConnect()
				if connect:
					connect.addAuthCallback(self.onRemoteConnectAuth)
					connect.setConnectCloseCallBack(self.fileno(),self.onRemoteConnectClose)
				else:
					self.close()
# 	def onRemoteConnectRecv(self,connect,data):
# 		self.send(data)
	def onRemoteConnectClose(self,connect):
		self.close()
	def onRemoteConnectAuth(self,connect):
		"""
		@type connect: remoteServerConnectLocalHander
		"""
		connect.setRecvCallback(self.fileno(), self.send)
		self.remoteConnect = connect
		self.onRecv("");
		self.connectName += str(connect)
	def onSend(self, data):
		sockConnect.onSend(self, data)
		if self.mode == "http":
			if self.messageParse.connection() == "close":
				self.close()
			self.messageParse.clear()
		
	def reseponse(self,data,ContentType="text/html",code=200):
		def httpdate():
			dt = datetime.now();
			weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
			month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
					"Oct", "Nov", "Dec"][dt.month - 1]
			return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
		        dt.year, dt.hour, dt.minute, dt.second)
		if type(data) is unicode:
			data = data.encode("utf-8")
		elif not type(data) is str:
			data = json.dumps(data)
			ContentType = "application/json"
		httpMessage = ""
		httpMessage += "HTTP/1.1 "+str(code)+" "+(httplib.responses[code])+"\r\n"
		httpMessage += "Server: DDDProxy/2.0\r\n"
		httpMessage += "Date: "+httpdate()+"\r\n"
		httpMessage += "Content-Length: "+str(len(data))+"\r\n"
		httpMessage += "Content-Type: "+ContentType+"\r\n"
		httpMessage += "Connection: "+self.messageParse.connection()+"\r\n"
		
# 		connection = self.messageParse.getHeader("connection")
		
		baseServer.log(1,self,code,ContentType,httpMessage)
		
		httpMessage += "\r\n"
		httpMessage += data
		
		self.send(httpMessage)
	
	def getFileContent(self,name):
		content = None
		try:
			f = dirname(__file__)+"/template"+name
			f = open(f)
			content = f.read()
			f.close()
		except:
			pass
		return content
	
	def onHTTP(self,header,method,path,query,post):
		baseServer.log(1,self,header,method,path,query,post)
		if method == "POST":
			data = json.loads(post)
			opt = data["opt"]
			respons = {}
			if(opt=="serverList"):
				respons["pac"] = "http://"+self.messageParse.getHeader("host")+"/pac"
				respons["list"] = settingConfig.setting(settingConfig.remoteServerList)
			elif opt=="setServerList":
				settingConfig.setting(settingConfig.remoteServerList,data["data"])
				respons["status"] = "ok"
			elif opt=="testRemoteProxy":
				respons["status"] = "unknow"
			self.reseponse(respons)
		elif path == "/pac":
			content = self.getFileContent("/pac.js")
			domainList = domainConfig.config.getDomainOpenedList()
			domainListJs = ""
			for domain in domainList:
				domainListJs += "A(\""+domain+"\")||"
			content = content.replace("{{domainList}}",domainListJs)
			content = content.replace("{{proxy_ddr}}",self.messageParse.getHeader("host"))
			self.reseponse(content)
		elif path == "/api_status":
			connects = {}
			for handler in self.server.socketList.values():
				connect = handler.address[0]
				if not connect in connects:
					connects[connect] = []
				info = {"name":str(handler),"id":handler.fileno()}
				info.update(handler.info)
				connects[connect].append(info)
			self.reseponse({"connect":connects})
		else:
			if path == "/":
				path = "/index.html"
			content = self.getFileContent(path)
			if content:
				self.reseponse(content)
			else:
				self.reseponse("\""+path+"\" not found",code=404)
		

