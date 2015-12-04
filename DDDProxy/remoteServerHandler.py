#!/usr/bin/env python
# -*- coding: utf-8 -*-
import hashlib
import os
import ssl
import struct
import time

from configFile import configFile
from baseServer import sockConnect
from hostParser import parserUrlAddrPort
from socetMessageParser import httpMessageParser
from DDDProxy import log
from DDDProxy.symmetryConnectServerHandler import symmetryConnectServerHandler,\
	symmetryConnect
import json
import urlparse
import re

remoteAuth = ""

class realServerConnect(symmetryConnect):
	def __init__(self, server):
		symmetryConnect.__init__(self, server)
		self.messageParse = httpMessageParser()
		self.proxyMode = False
# 	def onConnected(self):
# 		sockConnect.onConnected(self)

		
	def onHTTP(self,  method):
		try:
			if method == "POST":
				self.sendDataToSymmetryConnect(self.makeReseponse(self.server.dumpConnects(),
									connection=self.messageParse.connection(),
									header={"Access-Control-Allow-Origin":self.messageParse.getHeader("origin")}))
				return
		except:
			log.log(3)
		self.sendDataToSymmetryConnect(self.makeReseponse("1", code=405))

	def onSymmetryConnectData(self, data):
		if self.proxyMode:
			self.send(data)
			return
		if self.messageParse.appendData(data):
			method = self.messageParse.method()
			path = self.messageParse.path()
			
			if method == "CONNECT":
				path = "https://"+path
				self.sendDataToSymmetryConnect("HTTP/1.1 200 OK\r\n\r\n")
				self.proxyMode = True
			addr,port = parserUrlAddrPort(path)
			if addr.find("status.dddproxy.com")>0:
				path = path.split("?")
				self.onHTTP(method)
			elif addr in ["127.0.0.1","localhost"]:
				self.server.addCallback(self.onClose)
			else:
				if method != "CONNECT":
					m = re.search("^(?:(?:http)://[^/]+)(.*)$", path)
					if m:
						dataCache = "%s %s %s\r\n"%(method,m.group(1),self.messageParse.httpVersion())
						dataCache += self.messageParse.HeaderString()+"\r\n"
						dataCache += self.messageParse.getBody()
						self.send(dataCache)
					else:
						self.close()
						
					self.connectName =  "	<	" + self.filenoStr()+" "+self.messageParse.method()+" "+self.messageParse.path()					
					self.messageParse.clear()
# 					print addr,port,dataCache
				if self.connectStatus() == 0:
					self.connect((addr,port))

	
class remoteServerHandler(symmetryConnectServerHandler):
	
	def __init__(self, *args, **kwargs):
		symmetryConnectServerHandler.__init__(self, *args, **kwargs)
		self.authPass = False

	def _setConnect(self, sock, address):
# 		symmetryConnectServerHandler._setConnect(self, sock, address)
		sockConnect._connectPool.apply_async(self.wrapToSll,sock,address)
	def onConnected(self):
		symmetryConnectServerHandler.onConnected(self)
		self.connectName = "[remote:"+str(self.fileno())+"]	"+self.address[0]
	def wrapToSll(self,sock, address,setThreadName):
		try:
			createSSLCert()
			sock = ssl.wrap_socket(sock, certfile=SSLCertPath,keyfile=SSLKeyPath, server_side=True)
			self.server.addCallback(symmetryConnectServerHandler._setConnect,self, sock, address)
		except:
			log.log(3)
			self.server.addCallback(self.onClose)
	def getSymmetryConnect(self, symmetryConnectId):
		symmetryConnect = symmetryConnectServerHandler.getSymmetryConnect(self, symmetryConnectId)
		if not symmetryConnect and self.authPass:
			symmetryConnect = realServerConnect(self.server)
			self.addSymmetryConnect(symmetryConnect, symmetryConnectId)
		return symmetryConnect
		
	def onServerToServerMessage(self, serverMessage):
		opt = serverMessage["opt"]
		if opt == "auth":
			timenum = serverMessage["time"]
			if time.time()-1800 < timenum and time.time()+1800 > timenum and self.authMake(remoteAuth, timenum)["password"] == serverMessage["password"]:
				self.authPass = True
				self.sendData(symmetryConnectServerHandler.serverToServerJsonMessageConnectId, json.dumps({"opt":"auth","status":"ok"}))
			else:
				log.log(2,"auth failed",serverMessage,self.authMake(remoteAuth, timenum))
				self.close()
	def onClose(self):
		symmetryConnectServerHandler.onClose(self)
SSLCertPath = configFile.makeConfigFilePathName("dddproxy.remote.cert")
SSLKeyPath = configFile.makeConfigFilePathName("dddproxy.remote.key")
def createSSLCert():
	if not os.path.exists(SSLCertPath) or not os.path.exists(SSLCertPath):
		shell = "openssl req -new -newkey rsa:1024 -days 3650 -nodes -x509 -subj \"/C=US/ST=Denial/L=Springfield/O=Dis/CN=ddd\" -keyout %s  -out %s"%(
																							SSLKeyPath,SSLCertPath)
		os.system(shell)
	