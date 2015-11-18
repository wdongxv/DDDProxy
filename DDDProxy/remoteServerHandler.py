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

remoteAuth = ""

class realServerConnect(symmetryConnect):
	def __init__(self, server):
		symmetryConnect.__init__(self, server)
		self.messageParse = httpMessageParser()
		self.dataCache = ""

		self.waitLocalConnectResponse = False


	def pauseSendAndRecv(self):
		return self.waitLocalConnectRecvRespons

	def onRecv(self, data):
		symmetryConnect.onRecv(self, data)
		self.waitLocalConnectRecvRespons = True
		self.sendToLocalData(data)
	def onConnected(self):
		sockConnect.onConnected(self)
		if self.messageParse.method() == "CONNECT":
			self.sendDataToSymmetryConnect("HTTP/1.1 200 OK\r\n\r\n")
		self.connectName = self.handler.filenoStr() + "	<	" + self.filenoStr()+" "+self.messageParse.method()+" "+self.messageParse.path()
		if self.dataCache:
			self.onSymmetryConnectData("")
		
	def onHTTP(self,  method):
		try:
			if method == "POST":
				self.requestSendToLocalDataCache.append(self.makeReseponse(self.server.dumpConnects(),
									connection=self.messageParse.connection(),
									header={"Access-Control-Allow-Origin":self.messageParse.getHeader("origin")}))
				return
		except:
			log.log(3)
		self.requestSendToLocalDataCache.append(self.makeReseponse("1", code=405))

	def onSymmetryConnectData(self, data):
		self.dataCache += data
		if self.sock:
			if self.dataCache:
				self.send(self.dataCache)
				self.dataCache = ""
			return
		if self.messageParse.appendData(data):
			method = self.messageParse.method()
			path = self.messageParse.path()
			
			if method == "CONNECT":
				path = "https://"+path
				self.dataCache = ""
			addr,port = parserUrlAddrPort(path)
			if addr.find("status.dddproxy.com")>0:
				path = path.split("?")
				self.onHTTP(method)
			elif addr in ["127.0.0.1","localhost"]:
				self.server.addCallback(self.onClose)
			else:
				self.connect((addr,port))


	
class remoteServerHandler(symmetryConnectServerHandler):
	
	def __init__(self, *args, **kwargs):
		symmetryConnectServerHandler.__init__(self, *args, **kwargs)
		self.authPass = False

	def _setConnect(self, sock, address):
		sockConnect._connectPool.apply_async(self.wrapToSll,sock,address)
		self.connectName = "[remote:"+str(self.fileno())+"]	"+self.address[0]
	def wrapToSll(self,sock, address):
		try:
			createSSLCert()
			sock = ssl.wrap_socket(sock, certfile=SSLCertPath,keyfile=SSLKeyPath, server_side=True)
			symmetryConnectServerHandler._setConnect(self, sock, address)	
			self.server.addCallback(symmetryConnectServerHandler._setConnect,self, sock, address)
		except:
			log.log(3)
			self.server.addCallback(self.onClose)


	def getRealConnect(self,symmetryConnectId):
		if symmetryConnectId in self.symmetryConnectList:
			return self.symmetryConnectList[symmetryConnectId]
		connect = realServerConnect(self.server)
		self.addSymmetryConnect(connect, symmetryConnectId)
		return connect
	def onServerToServerMessage(self, serverMessage):
		opt = serverMessage["opt"]
		if opt == "auth":
			timenum = serverMessage["time"]
			if time.time()-1800 < timenum and time.time()+1800 > timenum and self.authMake(remoteAuth, timenum) == serverMessage["password"]:
				self.authPass = True
				self.sendData(symmetryConnectServerHandler.serverToServerJsonMessageConnectId, json.dumps({"opt":"auth","status":"ok"}))
			else:
				self.close()

SSLCertPath = configFile.makeConfigFilePathName("dddproxy.remote.cert")
SSLKeyPath = configFile.makeConfigFilePathName("dddproxy.remote.key")
def createSSLCert():
	if not os.path.exists(SSLCertPath) or not os.path.exists(SSLCertPath):
		shell = "openssl req -new -newkey rsa:1024 -days 3650 -nodes -x509 -subj \"/C=US/ST=Denial/L=Springfield/O=Dis/CN=ddd\" -keyout %s  -out %s"%(
																							SSLKeyPath,SSLCertPath)
		os.system(shell)
	