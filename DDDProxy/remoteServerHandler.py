#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import re
import socket
import struct
import time

from . import log
from .symmetryConnectServerHandler import symmetryConnectServerHandler, \
	symmetryConnect
from .hostParser import parserUrlAddrPort
from .socetMessageParser import httpMessageParser

remoteAuth = ""

class realServerConnect(symmetryConnect):
	def __init__(self, server):
		symmetryConnect.__init__(self, server)
		self.messageParse = httpMessageParser()
		self.proxyMode = False
	def onHTTP(self, method):
		try:
			if method == "POST":
				origin = self.messageParse.getHeader("origin")
				self.sendDataToSymmetryConnect(self.makeReseponse(self.server.dumpConnects(),
									connection=self.messageParse.connection(),
									header={"Access-Control-Allow-Origin":origin}  if origin else {} ))
				return
		except:
			log.log(3)
		self.sendDataToSymmetryConnect(self.makeReseponse("1", code=405))
	def connect(self, address,  cb=None):
		
		def connectOk(ok):
			if not ok:
				self.server.addCallback(self.onClose)			
			if cb:
				cb(ok)
			
		addr = address[0]
		if addr in ["127.0.0.1", "localhost"] or re.match("192\.168.+", addr):
			return connectOk(False)
		symmetryConnect.connect(self, address,  cb=connectOk)
		
	def onSymmetryConnectData(self, data):
		if self.proxyMode:
			self.send(data)
			return
		
		if len(data) and data[0] == 5:  # socks5
# 			print "local >> ", len(data), binascii.b2a_hex(data)
			if (data[1] == 2 or data[1] == 1) and len(data) <= 4:
				self.sendDataToSymmetryConnect(b"\x05\x00")
			elif data[1] == 1:
				def connectOk(ok):
					if ok:
						send = b"\x05\x00\x00\x01"
						local = self._sock.getsockname()  
						send += socket.inet_aton(local[0]) + struct.pack(">H", local[1])  
					else:
						send = b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00"
# 					print "local << ", len(send), binascii.b2a_hex(send)
					self.sendDataToSymmetryConnect(send)
					self.proxyMode = True
				host = "<None>"
				if data[3] ==1:
					host = "%d.%d.%d.%d" % (data[4],data[5],data[6],data[7])
					port = data[8] * 0x100 + data[9]
					return self.connect((host, port), cb=connectOk)
				elif data[3] == 3:
					hostendindex = 5 + data[4]
					host = data[5:hostendindex].decode()
					port = data[hostendindex] * 0x100 + data[hostendindex + 1]
					return self.connect((host, port), cb=connectOk)
				else:
					reply = b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00"

# 				self.connectName = "	<	%s	Socks5:%s(%s)" % (self.filenoStr(), host, self.addressIp)
				self.sendDataToSymmetryConnect(reply)
			else:
				self.close()
		elif len(data) and  data[0] == 4:  # socks4/socks4a
			def connectOk(ok):
				if ok:
					send = b"\x00\x5A" + data[2:8]
				else:
					send = b"\x00\x5B"
# 				print "local << ", len(send), binascii.b2a_hex(send)
				self.sendDataToSymmetryConnect(send)
				self.proxyMode = True
# 			print "local >> ", len(data), binascii.b2a_hex(data)
			if data[1] == 1 or data[1] == 2:
				host = "%d.%d.%d.%d" % (data[4], data[5],data[6],data[7])
				version = "Socks4"
				if host.startswith("0.0.0.") and data[7] != 0:  # socks4a
					splits = data[8:].decode().split("\x00")
					host = splits[-2]
					version = "Socks4a"
				port = data[2] * 0x100 + data[3]
# 				self.connectName = "	<	%s	%s:%s(%s)" % (self.filenoStr(), version, host, self.addressIp)
				return self.connect((host, port), cb=connectOk)
			else:
				self.sendDataToSymmetryConnect(b'\x04\x91')
				self.close()
		else:
			httpmessagedone = self.messageParse.appendData(data)
			if self.messageParse.headerOk():
				method = self.messageParse.method()
				path = self.messageParse.path()
				connectOk = None
				if method == "CONNECT":
					path = "https://" + path
					def _connectOk(ok):
						if ok:
							self.sendDataToSymmetryConnect(b"HTTP/1.1 200 OK\r\n\r\n")
						else:
							self.sendDataToSymmetryConnect(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
					connectOk = _connectOk
					self.proxyMode = True
				addr, port = parserUrlAddrPort(path)
				if addr.find("status.dddproxy.com") > 0:
					path = path.split("?")
					if httpmessagedone:
						self.onHTTP(method)
				else:
					if self.connectStatus() == 0:
						if method != "CONNECT":
							m = re.search("^(?:(?:http)://[^/]+)(.*)$", path)
							if m:
								def _connectOk(ok):
									if not ok:
										return self.sendDataToSymmetryConnect(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
									dataCache = "%s %s %s\r\n" % (method, m.group(1), self.messageParse.httpVersion())
									dataCache += self.messageParse.HeaderString() + "\r\n"
									dataCache = dataCache.encode()
									dataCache += self.messageParse.readingBody()
									self.send(dataCache)
								connectOk = _connectOk
							else:
								self.close()
								return
# 							self.connectName = "	<	" + self.filenoStr() + " " + self.messageParse.method() + " " + self.messageParse.path()					
						self.connect((addr, port), cb=connectOk)
					elif self.connectStatus() == 1:
						self.send(self.messageParse.readingBody())
						if httpmessagedone:
							self.messageParse.clear()
			elif self.messageParse.headerError():
				self.close()
				
class remoteServerHandler(symmetryConnectServerHandler):
	def __init__(self, server,  *args, **kwargs):
		symmetryConnectServerHandler.__init__(self, server, remoteAuth, *args, **kwargs)
	def __str__(self, *args, **kwargs):
		return "[remote:" + str(self.fileno()) + "]	" + self.address[0]
# 		return symmetryConnectServerHandler.__str__(self, *args, **kwargs)
	def onConnected(self):
		symmetryConnectServerHandler.onConnected(self)
	def getSymmetryConnect(self, symmetryConnectId):
		symmetryConnect = symmetryConnectServerHandler.getSymmetryConnect(self, symmetryConnectId)
		if not symmetryConnect:
			symmetryConnect = realServerConnect(self.server)
			self.addSymmetryConnect(symmetryConnect, symmetryConnectId)
		return symmetryConnect
