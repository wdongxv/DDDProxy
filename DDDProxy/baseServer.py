# -*- coding: UTF-8 -*-
'''
Created on 2015年9月3日

@author: dxw
'''
import os
import select
import socket
import ssl
import threading
import time

from ThreadPool import ThreadPool
from configFile import configFile
from DDDProxy import log
import json
from datetime import datetime
import httplib



socket.setdefaulttimeout(5)
socketBufferMaxLenght = 1024 * 4


class sockConnect(object):
	"""
	@type sock: _socketobject
	"""
	
	_filenoLoop = 0

	socketEventCanRecv = "r"
	socketEventCanSend = "s"
	socketEventExcept = "e"

	def __init__(self, server):
		self.server = server
		self.info = {
					"startTime":int(time.time()),
					"send":0,
					"recv":0
					}
		self.makeAlive()
		self.sock = None
		self.address = (None, None)
		sockConnect._filenoLoop += 1
		self._fileno = sockConnect._filenoLoop
		self.connectName = ""

		self._sendPendingCache = ""
		
		self._requsetClose = False
		
	def fileno(self):
		return self._fileno
	def onConnected(self):
		pass
	def onRecv(self, data):
		pass
	def onSend(self, data):
		pass
	def onClose(self):
		pass

# 	connect to host

	_createCertLock = threading.RLock()
	def fetchRemoteCert(self, remoteServerHost, remoteServerPort):
		ok = False
		sockConnect._createCertLock.acquire()
		try:
			if not os.path.exists(self.SSLLocalCertPath(remoteServerHost, remoteServerPort)):
				cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerPort))
				open(self.SSLLocalCertPath(remoteServerHost, remoteServerPort), "wt").write(cert)
			ok = True
		except:
			log.log(3, remoteServerHost, remoteServerPort)
		sockConnect._createCertLock.release()
		return ok
	def SSLLocalCertPath(self, remoteServerHost, remoteServerPort):
		return configFile.makeConfigFilePathName("%s-%d.pem" % (remoteServerHost, remoteServerPort))
	_connectPool = ThreadPool(maxThread=100)
	def _doConnectSock(self, address, useSsl=False, cb=None, setThreadName=None):
		ok = True
		try:
			sock = None
			setThreadName("connect %s:%s" % (address[0], address[1]))
			addr = (socket.gethostbyname(address[0]), address[1])
			if useSsl:
				if self.fetchRemoteCert(address[0], address[1]):
					sock = ssl.wrap_socket(
								sock	=		socket.socket(socket.AF_INET, socket.SOCK_STREAM),
								ca_certs	=	self.SSLLocalCertPath(address[0], addr[1]),
								cert_reqs	=	ssl.CERT_REQUIRED)
			else:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

			if sock:
				sock.connect(addr)
			else:
				ok = False
		except:
			log.log(3, address)
			ok = False
		if ok:
			self.server.addCallback(self._setConnect, sock, address)
		else:
			self.server.addCallback(self.onClose)
		
		if cb:
			self.server.addCallback(cb, self if ok else None)
	def _setConnect(self, sock, address):
		"""
		@type sock: _socketobject
		"""
		self.sock = sock
		self.address = address
		self.server.addSockConnect(self)
		self.onConnected()

# 	send method

	def getSendPending(self):
		return len(self._sendPendingCache)
	def getSendData(self, length):
		data = self._sendPendingCache[:length]
		self._sendPendingCache = self._sendPendingCache[length:]
		return data

# 	client operating
	
	def connect(self, address, useSsl=False, cb=None):
		address = address
		sockConnect._connectPool.apply_async(self._doConnectSock, address, useSsl, cb)
	def send(self, data):
		if self._requsetClose:
			return
		self._sendPendingCache += data
	def close(self):
		self._requsetClose = True
	def shutdown(self):
		try:
			self.sock.shutdown()
		except:
			pass
		self.sock = None
		self.server.removeSocketConnect(self)
		self.server.addCallback(self.onClose)

# 	for server

	def pauseSendAndRecv(self):
		return False
	def _onReadyRecv(self):
		data = None
		
		try:
			data = self.sock.recv(socketBufferMaxLenght)
		except ssl.SSLError as e:
			if e.errno == 2:
				return
			log.log(3)
		except:
			log.log(3)
		
		if data:
			if isinstance(self.sock, ssl.SSLSocket):
				while 1:
					data_left = self.sock.pending()
					if data_left:
						data += self.sock.recv(data_left)
					else:
						break
			self.info["recv"] += len(data)
			self.onRecv(data)
		else:
			self.shutdown()
	def _onReadySend(self):
		data = self.getSendData(socketBufferMaxLenght)
		if data:
			self.info["send"] += len(data)
			try:
				self.sock.send(data)
				self.onSend(data)
				return
			except:
				log.log(3)
		self.shutdown()
	def onSocketEvent(self, event):
		if event == sockConnect.socketEventCanRecv:
			self._onReadyRecv()
		elif event == sockConnect.socketEventCanSend:
			self._onReadySend()
		elif event == sockConnect.socketEventExcept:
			self.shutdown()
		self.makeAlive()
			
# 	for http
	def getFileContent(self, name):
		content = None
		try:
			f = open(name)
			content = f.read()
			f.close()
		except:
			pass
		return content

	def makeReseponse(self, data, ContentType="text/html", code=200, connection="close", header={}):	
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
		httpMessage += "HTTP/1.1 " + str(code) + " " + (httplib.responses[code]) + "\r\n"
		httpMessage += "Server: DDDProxy/2.0\r\n"
		httpMessage += "Date: " + httpdate() + "\r\n"
		httpMessage += "Content-Length: " + str(len(data)) + "\r\n"
		httpMessage += "Content-Type: " + ContentType + "\r\n"
		httpMessage += "Connection: " + connection + "\r\n"
		for k, v in header.items():
			httpMessage += k + ": " + v + "\r\n"
		httpMessage += "\r\n"
		httpMessage += data
		return httpMessage
	def reseponse(self, data, ContentType="text/html", code=200, connection="close", header={}):
		self.send(self.makeReseponse(data, ContentType, code, connection, header))

# other 

	def makeAlive(self):
		self.info["lastAlive"] = int(time.time())
	def __str__(self, *args, **kwargs):
		return self.connectName if self.connectName else  (self.filenoStr() + str(self.address))
	def filenoStr(self):
		return "[" + str(self.fileno()) + "]"

class baseServer():
	def __init__(self, handler):
		self.handler = handler

		self._socketConnectList = {}
		self.serverList = []

		self.callbackList = []

		socket.setdefaulttimeout(10)

	def addCallback(self, cb, *args, **kwargs):
		self.callbackList.append((cb, 0, args, kwargs))
	def addDelay(self, delay, cb, *args, **kwargs):
		self.callbackList.append((cb, delay + time.time(), args, kwargs))
		
	def addListen(self, port, host=""):
# 		self.server = bind_sockets(port=self.port, address=self.host) 
		log.log(1, "run in ", host, ":", port)
		server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		
		server.bind((host, port))
		server.listen(1024)
		self.addSockListen(server)
	def addSockListen(self, sock):
		"""
		@param sock: _socketobject
		"""
		sock.setblocking(False)
		self.serverList.append(sock)
# manager connect

	def addSockConnect(self, connect):
		if not connect.sock in self._socketConnectList:
			connect.sock.setblocking(False)
			try:
				connect.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
			except:
				pass
			
			try:
				connect.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
			except:
				pass
			try:
				connect.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
			except:
				pass
			try:
				TCP_KEEPALIVE = 0x10
				connect.sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 3)
			except:
				pass
			self._socketConnectList[connect.sock] = connect
	def removeSocketConnectBySocket(self, sock):
		if sock in self._socketConnectList:
			handler = self._socketConnectList[sock]
			del self._socketConnectList[sock]
			
	def removeSocketConnect(self, handler):
		for k, v in self._socketConnectList.items():
			if v == handler:
				del self._socketConnectList[k]
				break
	

	def start(self):
		
		while True:
			rlist = [] + self.serverList
			wlist = []
			currentTime = time.time()
			
			s_exceptional = []
			for connect in self._socketConnectList.values():
				if connect.info["lastAlive"] < currentTime - 3600:
					connect.shutdown()
					continue

				if connect.pauseSendAndRecv():
					continue
				rlist.append(connect.sock)
				if connect.getSendPending():
					wlist.append(connect.sock)
				elif connect._requsetClose:
					s_exceptional.append(connect.sock)
			try:
				s_readable, s_writable, _s_exceptional = select.select(rlist, wlist, rlist, 1)
				s_exceptional += _s_exceptional
			except:
				log.log(3)
				continue;
			for sock in s_readable:
				if sock in self.serverList:
					self.onConnect(sock)
				else:
					self.onSocketEvent(sock, sockConnect.socketEventCanRecv)
			for sock in s_writable:
				self.onSocketEvent(sock, sockConnect.socketEventCanSend)
			for sock in s_exceptional:
				self.onSocketEvent(sock, sockConnect.socketEventExcept)
				
			cblist = self.callbackList
			self.callbackList = []
			currentTime = time.time()
			for cbobj in cblist:
				if cbobj[1] <= currentTime:
					cbobj[0](*cbobj[2], **cbobj[3])
				else:
					self.callbackList.append(cbobj)
# 	for  sock event
	def onConnect(self, sock):
		sock, address = sock.accept()
		connect = self.handler(server=self)
		connect._setConnect(sock, address)
		log.log(2, connect, "*	connect")
	def onSocketEvent(self, sock, event):
		
		if sock in self._socketConnectList:
			connect = self._socketConnectList[sock]
			connect.onSocketEvent(event)
# other
	def dumpConnects(self):
		connects = {}
		for handler in self._socketConnectList.values():
			connect = handler.address[0]
			if not connect in connects:
				connects[connect] = []
			info = {"name":str(handler)}
			info.update(handler.info)
			connects[connect].append(info)
		
		for l in connects.values():
			l.sort(cmp=lambda x, y : cmp(y["send"] + y["recv"], x["send"] + x["recv"]))
		
		return {"connect":connects, "threads":sockConnect.connectPool.dump(), "currentTime":int(time.time())}

if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()
