#!/usr/bin/env python
# -*- coding: utf-8 -*-
from DDDProxy.server import ServerHandler, baseServer, DDDProxySocketMessage
import ssl
import Queue
import struct
import hashlib
import time
from DDDProxy import hostParser
import socket
from DDDProxy.socetMessageParser import socetMessageParser
import sys
import traceback
import DDDProxyConfig
import thread

	
class remoteServerHandler(ServerHandler):  
	def __init__(self, conn, addr, threadid):
		super(remoteServerHandler, self).__init__(conn, addr, threadid)
		
		DDDProxyConfig.createSSLCert()
		
		self.localProxy = ssl.wrap_socket(conn, certfile=DDDProxyConfig.SSLCertPath,
										keyfile=DDDProxyConfig.SSLKeyPath, server_side=True)
		self.threadid = threadid
		self.source_address = addr
		self.orignConn = None
		self.KeepAlive = False
		self.method = "GET"
		self.httpMessage = ""
		
		self.lock = Queue.Queue()

		self.localProxyMark = ""

		self.httpData = True
		
	def info(self):
		return "%s->%s	%s" % (self.localProxyMark, ServerHandler.info(self), self.httpMessage)
	def check(self):
		timeNumber = struct.unpack("i", self.localProxy.recv(4))[0]
		
		checkA = self.localProxy.recv(32)
		checkB = hashlib.md5("%s%d" % (DDDProxyConfig.remoteServerAuth, timeNumber)).hexdigest()
		timeRange = 3600
		baseServer.log(1, self.threadid, "check:", checkA, checkB, timeNumber, timeRange, time.time())
		if timeNumber < time.time() - timeRange or timeNumber > time.time() + timeRange or checkA != checkB:
			return False
		return True
	def openOrignConn(self, path):
		if self.orignConn is not None:
			return
		addr, port = hostParser.parserUrlAddrPort(path)
		ip = socket.gethostbyname(addr)
		self.orignConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.orignConn.connect((ip, port))
	
	def sourceToServer(self):
		try:
			# 接收消息头
			socetParser = socetMessageParser()
			hasData = False
			for data in DDDProxySocketMessage.recv(self.localProxy):
				baseServer.log(1, self.threadid, ">>>>>", data, len(data))
				socetParser.putMessage(data)
				if socetParser.messageStatus():
					self.httpMessage = socetParser.httpMessage()
					hasData = True
					break;
				self.markActive("recv header")
			
			if not hasData:
				return False

			# 连接原始服务器
			self.method, path, protocol = self.httpMessage
			if self.method:
				baseServer.log(2, self.localProxyMark, [self.source_address,self.threadid] (self.method, path, protocol))
			if self.method == "CONNECT":
				self.httpData = False
				self.openOrignConn("https://" + path);
				baseServer.log(1, self.threadid, "CONNECT ", path)
				DDDProxySocketMessage.send(self.localProxy, "HTTP/1.1 200 OK\r\n\r\n")
			else:
				self.httpData = True
				baseServer.log(1, self.threadid, ">>>>>", "openOrignConn")
				self.openOrignConn(path);
				baseServer.log(1, self.threadid, ">>>>>", socetParser.messageData())
				self.orignConn.send(socetParser.messageData())
			
			self.lock.put("ok")
			
			# 转发原始请求到原始服务器
			for data in DDDProxySocketMessage.recv(self.localProxy):
				self.orignConn.send(data);
				self.markActive("localProxy recv")

			self.close()
			return True
		except TypeError:
			pass
		except:
			baseServer.log(3, self.threadid, "sourceToServer error!!!")
		self.lock.put("error")
		self.close()
		return False
	def serverToSource(self):
		error = False
		baseServer.log(1, self.threadid, "----", "<")
		if self.lock.get() == "ok":
			try:
				count = 0;
				while True:
					if self.orignConn is None:
						break
					baseServer.log(1, self.threadid, "orignConn", "recv")
					tmp = self.orignConn.recv(DDDProxyConfig.cacheSize)
					if not tmp:
						break
					count += len(tmp)
					baseServer.log(1, self.threadid, "localProxy", "send", tmp)
					DDDProxySocketMessage.send(self.localProxy, tmp)
					baseServer.log(1, self.threadid, "localProxy", "send", "end")
					self.markActive("orignConn recv")
			except socket.timeout:
				pass
			except:
				baseServer.log(3, self.threadid, "serverToSource error!!!")
				error = True
		baseServer.log(1, self.threadid, "----", ">")
		return not error
	
	def close(self):

		try:
			if self.orignConn:
				self.orignConn.shutdown(0)
			self.orignConn = None
		except:
			pass
		
		try:
			if self.localProxy:
				DDDProxySocketMessage.end(self.localProxy)
		except:
			pass
		
		try:
			if self.localProxy:
				self.localProxy.shutdown(0)
			self.localProxy = None
		except:
			pass
		
		self.lock.put("close")

	def run(self):
		try:
			if self.check():
				self.localProxyMark = DDDProxySocketMessage.recvOne(self.localProxy);
				baseServer.log(1, self.threadid, "self.localProxyMark", self.localProxyMark)
				
				thread.start_new_thread(self.sourceToServer, tuple())
				self.serverToSource()
		except:
			baseServer.log(3)
		self.close()
		
		baseServer.log(1, self.threadid, "!!!!! threadid end")
		
	def error(self):
		pass
