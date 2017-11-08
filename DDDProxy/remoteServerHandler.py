#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import re
import socket
import ssl
import struct
import time

from DDDProxy import log
from DDDProxy.symmetryConnectServerHandler import symmetryConnectServerHandler, \
	symmetryConnect
from baseServer import sockConnect
from configFile import configFile
from hostParser import parserUrlAddrPort
from socetMessageParser import httpMessageParser


remoteAuth = ""

class realServerConnect(symmetryConnect):
	def __init__(self, server):
		symmetryConnect.__init__(self, server)
		self.messageParse = httpMessageParser()
		self.proxyMode = False
# 	def onConnected(self):
# 		sockConnect.onConnected(self)

	def onSend(self, data):
		symmetryConnect.onSend(self, data)		
	def onHTTP(self, method):
		try:
			if method == "POST":
				self.sendDataToSymmetryConnect(self.makeReseponse(self.server.dumpConnects(),
									connection=self.messageParse.connection(),
									header={"Access-Control-Allow-Origin":self.messageParse.getHeader("origin")}))
				return
		except:
			log.log(3)
		self.sendDataToSymmetryConnect(self.makeReseponse("1", code=405))
	def connect(self, address, useSsl=False, cb=None):
		addr = address[0]
		if addr in ["127.0.0.1", "localhost"] or re.match("192\.168.+", addr):
			return connectOk(False)
		symmetryConnect.connect(self, address, useSsl=useSsl, cb=cb)
	def onSymmetryConnectData(self, data):
		if self.proxyMode:
			self.send(data)
			return
		
		if len(data) and data[0] == '\x05':  # socks5
# 			print "local >> ", len(data), binascii.b2a_hex(data)
			if (data[1] == '\x02' or data[1] == '\x01') and len(data) <= 4:
				self.sendDataToSymmetryConnect(b"\x05\x00")
			elif data[1] == '\x01':
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
				if data[3] == '\x01':
					host = "%d.%d.%d.%d" % (ord(data[4]), ord(data[5]), ord(data[6]), ord(data[7]))
					port = ord(data[8]) * 0x100 + ord(data[9])
					return self.connect((host, port), cb=connectOk)
				elif data[3] == "\x03":
					hostendindex = 5 + ord(data[4])
					host = data[5:hostendindex]
					port = ord(data[hostendindex]) * 0x100 + ord(data[hostendindex + 1])
					return self.connect((host, port), cb=connectOk)
				else:
					reply = b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00"

				self.connectName = "	<	%s	Socks5:%s(%s)" % (self.filenoStr(), host, self.addressIp)
				self.sendDataToSymmetryConnect(reply)
			else:
				self.close()
		elif len(data) and  data[0] == '\x04':  # socks4/socks4a
			def connectOk(ok):
				if ok:
					send = b"\x00\x5A" + data[2:8]
				else:
					send = b"\x00\x5B"
# 				print "local << ", len(send), binascii.b2a_hex(send)
				self.sendDataToSymmetryConnect(send)
				self.proxyMode = True
# 			print "local >> ", len(data), binascii.b2a_hex(data)
			if data[1] == '\x01' or data[1] == '\x02':
				host = "%d.%d.%d.%d" % (ord(data[4]), ord(data[5]), ord(data[6]), ord(data[7]))
				version = "Socks4"
				if host.startswith("0.0.0.") and ord(data[7]) != 0:  # socks4a
					splits = data[8:].split("\x00")
					host = splits[-2]
					version = "Socks4a"
				port = ord(data[2]) * 0x100 + ord(data[3])
				self.connectName = "	<	%s	%s:%s(%s)" % (self.filenoStr(), version, host, self.addressIp)
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
						self.sendDataToSymmetryConnect("HTTP/1.1 200 OK\r\n\r\n")
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
									dataCache = "%s %s %s\r\n" % (method, m.group(1), self.messageParse.httpVersion())
									dataCache += self.messageParse.HeaderString() + "\r\n"
									dataCache += self.messageParse.readingBody()
									self.send(dataCache)
								connectOk = _connectOk
							else:
								self.close()
								
							self.connectName = "	<	" + self.filenoStr() + " " + self.messageParse.method() + " " + self.messageParse.path()					
						self.connect((addr, port), cb=connectOk)
					elif self.connectStatus() == 1:
						self.send(self.messageParse.readingBody())
						if httpmessagedone:
							self.messageParse.clear()

class remoteServerHandler(symmetryConnectServerHandler):
	
	def __init__(self, *args, **kwargs):
		symmetryConnectServerHandler.__init__(self, *args, **kwargs)
		self.authPass = False

	def _setConnect(self, sock, address):
# 		symmetryConnectServerHandler._setConnect(self, sock, address)
		sockConnect._connectPool.apply_async(self.wrapToSll, sock, address)
	def onConnected(self):
		symmetryConnectServerHandler.onConnected(self)
		self.connectName = "[remote:" + str(self.fileno()) + "]	" + self.address[0]
	def wrapToSll(self, sock, address, setThreadName):
		try:
			createSSLCert()
			sock = ssl.wrap_socket(sock, certfile=SSLCertPath, keyfile=SSLKeyPath, server_side=True)
			self.server.addCallback(symmetryConnectServerHandler._setConnect, self, sock, address)
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
			if time.time() - 1800 < timenum and time.time() + 1800 > timenum and self.authMake(remoteAuth, timenum)["password"] == serverMessage["password"]:
				self.authPass = True
				self.sendData(symmetryConnectServerHandler.serverToServerJsonMessageConnectId, json.dumps({"opt":"auth", "status":"ok"}))
			else:
				log.log(2, "auth failed", serverMessage, self.authMake(remoteAuth, timenum))
				self.close()
		else:
			symmetryConnectServerHandler.onServerToServerMessage(self, serverMessage)
	def onClose(self):
		symmetryConnectServerHandler.onClose(self)
SSLCertPath = configFile.makeConfigFilePathName("dddproxy.remote.cert")
SSLKeyPath = configFile.makeConfigFilePathName("dddproxy.remote.key")
def createSSLCert():
	if not os.path.exists(SSLCertPath) or not os.path.exists(SSLCertPath):
		shell = "openssl req -new -newkey rsa:1024 -days 3650 -nodes -x509 -subj \"/C=US/ST=Denial/L=Springfield/O=Dis/CN=ddd\" -keyout %s  -out %s" % (
																							SSLKeyPath, SSLCertPath)
		os.system(shell)
	
