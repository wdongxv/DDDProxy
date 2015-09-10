#!/usr/bin/env python
# -*- coding: utf-8 -*-
import hashlib
import math
import struct
import time

from baseServer import baseServer
from baseServer import sockConnect
from socetMessageParser import httpMessageParser
import os
import ssl
import socket
from hostParser import parserUrlAddrPort

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
				if dataSize>0:
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
			self.connect(parserUrlAddrPort(path))
	def onConnected(self):
		sockConnect.onConnected(self)
		if self.messageParse.method() == "CONNECT":
			self.handler.sendData(self.connectId,"HTTP/1.1 200 OK\r\n\r\n")
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
	
	def __init__(self, server, *args, **kwargs):
		sockConnect.__init__(self, server, *args, **kwargs)
		messageHandler.__init__(self)
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
		for connectId,cb in self.connectCloseCallback.items():
			cb(self)
		self.connectCloseCallback = {}
		self.recvCallback = {}
	def onMessage(self,connectId,data):
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
	def sendOpt(self,connectId,opt):
		self.send(self.optChunk(connectId, opt))
	def sendData(self,connectId,data):
		for d in self.dataChunk(connectId, data):
			self.send(d)
			
	def onRecv(self,data):
		sockConnect.onRecv(self, data)
		self.appendData(data)
		
	def authMake(self,auth,timenum):
		return struct.pack("i", timenum)+hashlib.md5("%s%d" % (auth, timenum)).hexdigest()
	
class remoteConnectServerHandler(remoteServerConnect):  
	def __init__(self, *args, **kwargs):
		remoteServerConnect.__init__(self, *args, **kwargs)
		self.realConnectList = {}
		self.authPass = False
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
		if connectId==-1:
			size = struct.calcsize("i")
			timenum = struct.unpack("i",data[:size])[0]
			if time.time()-300 < timenum and time.time()+300 > timenum and self.authMake(remoteAuth, timenum)==data:
				self.authPass = True
				self.sendOpt(-1, remoteServerConnect.optAuthOK)
			else:
				self.close()
		elif self.authPass:
			self.getRealConnect(connectId).onlocalRecv(data)
	def onClose(self):
		for connect in self.realConnectList.values():
			connect.close()
		remoteServerConnect.onClose(self)
SSLCertPath = "/tmp/dddproxy.remote.cert"
SSLKeyPath = "/tmp/dddproxy.remote.key"
def createSSLCert():
	if not os.path.exists(SSLCertPath) or not os.path.exists(SSLCertPath):
		shell = "openssl req -new -newkey rsa:1024 -days 3650 -nodes -x509 -subj \"/C=US/ST=Denial/L=Springfield/O=Dis/CN=ddd\" -keyout %s  -out %s"%(
																							SSLKeyPath,SSLCertPath)
		os.system(shell)
	