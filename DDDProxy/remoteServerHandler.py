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
import json


remoteAuth = "1"

class messageHandler:
	_headSize = struct.calcsize("iH")
	def __init__(self):
		self.buffer = ""
	def onMessage(self,connectId,data):
		raise NotImplementedError()
	def onOpt(self,connectId,opt):
		raise NotImplementedError()
	def appendData(self, data):
		self.buffer += data
		while True:
			bufferLen = len(self.buffer)
			_headSize = messageHandler._headSize
			if bufferLen >= _headSize:
				connectId,dataSize = struct.unpack("ih",self.buffer[:_headSize])
				if dataSize>=0:
					endIndex = dataSize+_headSize
					if bufferLen > endIndex:
						dataMessage = self.buffer[_headSize:endIndex]
						self.buffer = self.buffer[endIndex+1:]
						self.onMessage(connectId, dataMessage)
					else:
						break
				else:
					self.buffer = self.buffer[_headSize+1:]
					self.onOpt(connectId, dataSize)
			else:
				break	
	
	def optChunk(self,connectId,opt):
		if opt >=0:
			raise Exception("opt must > 0")
		return struct.pack("i", connectId)+struct.pack("h", opt) +"\n"
	
	def dataChunk(self,connectId,data):
		l = len(data)
		if l > 32767:  #分块
			yield self.sendData(connectId, data[:32767])
			yield self.sendData(connectId, data[32767:])
		else:
			yield struct.pack("i", connectId)+struct.pack("h", l) +data+"\n"
		
class realServerConnect(sockConnect):
	def __init__(self, handler,connectId):
		sockConnect.__init__(self, handler.server)
		self.handler = handler
		self.connectId = connectId
		
		self.messageParse = httpMessageParser()
		self.dataCache = ""
		
		self.closeCallbackList = []
		
	def onRecv(self,data):
		"""
		从真实服务器到本机
		"""
		sockConnect.onRecv(self, data)
		self.handler.sendData(self.connectId,data)
	def onlocalRecv(self,data):
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
	def onHTTP(self,  method):
		
		try:
			if method == "POST":
# 				postJson = json.loads(self.messageParse.getBody())
				self.handler.sendData(self.connectId,
					self.makeReseponse(self.server.dumpConnects(),
									connection=self.messageParse.connection(),
									header={"Access-Control-Allow-Origin":self.messageParse.getHeader("origin")}))
				return
		except:
			log.log(3)
		self.handler.sendData(self.connectId,self.makeReseponse("1", code=405))

# 	def __str__(self, *args, **kwargs):
# 		return self.handler.filenoStr() + " << " + self.filenoStr() + str(self.address)
				
	def onConnected(self):
		sockConnect.onConnected(self)
		if self.messageParse.method() == "CONNECT":
			self.handler.sendData(self.connectId,"HTTP/1.1 200 OK\r\n\r\n")
		self.connectName = self.handler.filenoStr() + "	<	" + self.filenoStr()+" "+self.messageParse.method()+" "+self.messageParse.path()
		if self.dataCache:
			self.onlocalRecv("")
	def onClose(self):
		while len(self.closeCallbackList):
			self.server.addCallback(self.closeCallbackList.pop(0),self)
		sockConnect.onClose(self)
		
class remoteServerConnect(sockConnect,messageHandler):
	optCloseConnect = -1
	optAuthOK = -2
	optAuthError = -3
	optServerPing = -4
	optServerPingRespones = -5


	serverToServerJsonMessageConnectId = -2

	
	serverPing_MessagePauseCacheLimit = 500
		
	def __init__(self, server, *args, **kwargs):
		sockConnect.__init__(self, server, *args, **kwargs)
		messageHandler.__init__(self)

		self.serverPing_MessagePauseCount = 0
		self.serverPing_MessagePauseCache = []
		self.serverPing = False
		
		self.recvCallback = {}
		self.connectCloseCallback = {}
	def setConnectCloseCallBack(self,connectid,cb):
		self.connectCloseCallback[connectid] = cb
	def setRecvCallback(self,connectId,callback):
		self.recvCallback[connectId] = callback
	def removeAllCallback(self,connectId):
		if connectId in self.recvCallback:
			del self.recvCallback[connectId]
		if connectId in self.connectCloseCallback:
			del self.connectCloseCallback[connectId]
	
	
	def onClose(self):
		for cb in self.connectCloseCallback.values():
			self.server.addCallback(cb,self)
		self.connectCloseCallback = {}
		self.recvCallback = {}
	def onMessage(self,connectId,data):
		if connectId == remoteServerConnect.serverToServerJsonMessageConnectId:
			serverMessage = json.loads(data)
			for k,v in serverMessage.items():
				if k == "serverPing" and self.serverPing != v:
					self.serverPing = v
					self.sendData(connectId, json.dumps({"serverPing":v}))
		else:
			cb = self.recvCallback[connectId] if connectId in self.recvCallback else None
			if cb:
				cb(data)
			else:
				self.sendOpt(connectId, remoteServerConnect.optCloseConnect)
	def onOpt(self,connectId,opt):
		if opt==remoteServerConnect.optCloseConnect:
			if connectId in self.connectCloseCallback:
				self.connectCloseCallback[connectId](self)
				del self.connectCloseCallback[connectId]
		elif connectId == remoteServerConnect.serverToServerJsonMessageConnectId:
			if opt==remoteServerConnect.optServerPing:
				self.sendOpt(remoteServerConnect.serverToServerJsonMessageConnectId , remoteServerConnect.optServerPingRespones)
			elif opt ==  remoteServerConnect.optServerPingRespones:
				self.serverPing_MessagePauseCount = 0;
				cache = self.serverPing_MessagePauseCache
				self.serverPing_MessagePauseCache = []
				for i in cache:
					self.sendData(i[0],[1])
	def sendOpt(self,connectId,opt):
		self.send(self.optChunk(connectId, opt))
	
	def sendData(self,connectId,data):
		if self.serverPing:
			self.serverPing_MessagePauseCount += 1
			if self.serverPing_MessagePauseCount >= remoteServerConnect.serverPing_MessagePauseCacheLimit:
				if self.serverPing_MessagePauseCount == remoteServerConnect.serverPing_MessagePauseCacheLimit:
					self.sendOpt(remoteServerConnect.serverToServerJsonMessageConnectId, remoteServerConnect.optServerPing)
				self.serverPing_MessagePauseCache.append([connectId,data])
				return
			
		
		for d in self.dataChunk(connectId, data):
			self.send(d)
	
	def setServerPing(self,isOpen=True):
		self.sendData( remoteServerConnect.serverToServerJsonMessageConnectId,
					json.dumps({"serverPing":isOpen}))
	def onRecv(self,data):
		sockConnect.onRecv(self, data)
		self.appendData(data)
		
	def authMake(self,auth,timenum):
		return struct.pack("i", timenum)+hashlib.md5("%s%d" % (auth, timenum)).hexdigest()
	
class remoteServerHandler(remoteServerConnect):
	serverToServerAuthConnectId = -1
	
	def __init__(self, *args, **kwargs):
		remoteServerConnect.__init__(self, *args, **kwargs)
		self.realConnectList = {}
		self.authPass = False
	
	def wrapToSll(self,setThreadName=None):
		try:
			setThreadName(str(self)+"wrapToSll")
			createSSLCert()
			self.sock = ssl.wrap_socket(self.sock, certfile=SSLCertPath,keyfile=SSLKeyPath, server_side=True)
			self.server.addCallback(remoteServerConnect.onConnected,self)
		except:
			log.log(3)
			self.server.addCallback(self.onClose)
	def onConnected(self):
		sockConnect.connectPool.apply_async(self.wrapToSll)
		self.connectName = "[remote:"+str(self.fileno())+"]	"+self.address[0]

	def onRealConnectClose(self,connect):
		"""
		@param connect:realServerConnect 
		"""
		self.sendOpt(connect.connectId, remoteServerConnect.optCloseConnect)
		if connect.connectId in self.realConnectList:
			del self.realConnectList[connect.connectId]
	def onOpt(self, connectId, opt):
		if connectId in self.realConnectList:
			connect = self.realConnectList[connectId]
			if opt == remoteServerConnect.optCloseConnect:
				connect.close()
			
	def getRealConnect(self,connectId):
		if connectId in self.realConnectList:
			return self.realConnectList[connectId]
		connect = realServerConnect(self,connectId)
		connect.closeCallbackList.append(self.onRealConnectClose)
		self.realConnectList[connectId] = connect
		return connect 
	def onMessage(self,connectId,data):
		if connectId>=0:
			if self.authPass:
				self.getRealConnect(connectId).onlocalRecv(data)
		elif connectId==remoteServerHandler.serverToServerAuthConnectId:
			size = struct.calcsize("i")
			timenum = struct.unpack("i",data[:size])[0]
			if time.time()-1800 < timenum and time.time()+1800 > timenum:
				if self.authMake(remoteAuth, timenum)==data:
					self.authPass = True
					self.sendOpt(-1, remoteServerConnect.optAuthOK)
				else:
					log.log(2,self,"auth not Math:",self.authMake(remoteAuth, timenum),repr(data))
			else:
				log.log(2,self,"timenum is Expired")
			if not self.authPass:
				self.close()
		else:
			remoteServerConnect.onMessage(self,connectId,data)
			
	def onClose(self):
		for connect in self.realConnectList.values():
			connect.close()
		remoteServerConnect.onClose(self)
		

SSLCertPath = configFile.makeConfigFilePathName("dddproxy.remote.cert")
SSLKeyPath = configFile.makeConfigFilePathName("dddproxy.remote.key")
def createSSLCert():
	if not os.path.exists(SSLCertPath) or not os.path.exists(SSLCertPath):
		shell = "openssl req -new -newkey rsa:1024 -days 3650 -nodes -x509 -subj \"/C=US/ST=Denial/L=Springfield/O=Dis/CN=ddd\" -keyout %s  -out %s"%(
																							SSLKeyPath,SSLCertPath)
		os.system(shell)
	