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
		self._sock = None
		self.address = (None, None)
		sockConnect._filenoLoop += 1
		self._fileno = sockConnect._filenoLoop
		self.connectName = ""

		self._sendPendingCache = ""
		
		self._requsetClose = False
		
		self._connecting = False
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

	def connectStatus(self):
		"""
		0:none
		1:connected
		2:connecting"""
		if self._sock:
			return 1
		else:
			if self._connecting:
				return 2
		return 0
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
		self._connecting = True
		ok = True
		try:
			sock = None
			threadName = "connect %s:%s" % (address[0], address[1])
			log.log(1, threadName)
			setThreadName(threadName)
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
			self._connecting = False
			self.server.addCallback(self.onClose)
		
		if cb:
			self.server.addCallback(cb, self if ok else None)
	def _setConnect(self, sock, address):
		"""
		@type sock: _socketobject
		"""
		self._sock = sock
		self.address = address
		self.server.addSockConnect(self)
		self._connecting = False
		self.onConnected()

# 	send method

	def getSendPending(self):
		if self._requsetClose:
			return True
		return len(self._sendPendingCache)
	def getSendData(self, length):
		data = self._sendPendingCache[:length]
		self._sendPendingCache = self._sendPendingCache[length:]
		return data

# 	client operating
	
	def connect(self, address, useSsl=False, cb=None):
		if self.connectStatus():
			raise Exception(self, "connect status is", self.connectStatus())
		self._connecting = True
		address = address
		sockConnect._connectPool.apply_async(self._doConnectSock, address, useSsl, cb)
	def send(self, data):
		if self._requsetClose:
			return
		self._sendPendingCache += data
	def close(self):
		self._requsetClose = True
		self.makeAlive()
	def shutdown(self):
		try:
			self._sock.close()
# 			self._sock.shutdown()
		except:
			pass
		if self.server.removeSocketConnect(self):
			self._sock = None
			self.server.addCallback(self.onClose)
		
# 		self.close()
# 	for server

	def pauseSendAndRecv(self):
		return False
	def _onReadyRecv(self):
		data = None
		
		try:
			data = self._sock.recv(socketBufferMaxLenght)
		except ssl.SSLError as e:
			if e.errno == 2:
				return
			log.log(3,self)
		except:
			log.log(3,self)
		
		if data:
			if isinstance(self._sock, ssl.SSLSocket):
				while 1:
					data_left = self._sock.pending()
					if data_left:
						data += self._sock.recv(data_left)
					else:
						break
			self.info["recv"] += len(data)
			self.onRecv(data)
		else:
			log.log(2, self, "<<< data is pool,close")
			self.shutdown()
	def _onReadySend(self):
		while self.getSendPending():
			data = self.getSendData(socketBufferMaxLenght)
			if data:
				self.info["send"] += len(data)
				try:
					self._sock.send(data)
					self.onSend(data)
					continue
				except:
					log.log(3)
			else:
				log.log(2, self, "<<< request close")
				self.shutdown()
				break

	def onSocketEvent(self, event):
		if event == sockConnect.socketEventCanRecv:
			self._onReadyRecv()
		elif event == sockConnect.socketEventCanSend:
			self._onReadySend()
		elif event == sockConnect.socketEventExcept:
			self.shutdown()
			log.log(2, self, "<<< socketEventExcept, close")

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
		print "start server on: " + host + ":" + str(port)
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
		if not connect._sock in self._socketConnectList:
			connect._sock.setblocking(False)
			try:
				connect._sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
			except:
				pass
			
			try:
				connect._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
			except:
				pass
			try:
				connect._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
			except:
				pass
			try:
				TCP_KEEPALIVE = 0x10
				connect._sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 3)
			except:
				pass
			self._socketConnectList[connect._sock] = connect
	def removeSocketConnectBySocket(self, sock):
		if sock in self._socketConnectList:
			del self._socketConnectList[sock]
			
	def removeSocketConnect(self, handler):
		for k, v in self._socketConnectList.items():
			if v == handler:
				del self._socketConnectList[k]
				return True
		return False
	def startWithEpoll(self):
		try:
			epoll = select.epoll()
		except:
			return self.startWithKQueue()
		socketList = {}
		
		def epollProxy(rlist, wlist, xlist, timeout):
			for sock in xlist:
				if not sock in socketList:
					socketList[sock] = sock.fileno()
					epoll.register(sock.fileno(),select.EPOLLIN)
			s_readable = []
			s_writable = []
			s_writable.extend(x for x in wlist)
			s_exceptional = []
			for fd,event in epoll.poll(timeout):
				sock = None
				for _sock, _fd in socketList.items():
					if fd == _fd:
						sock = _sock
						break
# 				if sock in s_writable:
# 					s_writable.remove(sock)

				if select.EPOLLIN & event:
					s_readable.append(sock)
				elif select.EPOLLOUT & event:
					s_writable.append(sock)
				elif select.EPOLLERR & event or select.EPOLLHUP & event:
					epoll.unregister(fd)
					del socketList[sock]
					s_exceptional.append(sock)
				else:
					log.log(3,"unknow event",event) 
			return s_readable, s_writable, s_exceptional
		return self.start(poll=epollProxy)
	def startWithKQueue(self):
		try:
			kq = select.kqueue()
		except:
			return self.start()
		socketList = {}
		def kqueueProxy(rlist, wlist, xlist, timeout):
			for s in xlist:
				if not s in socketList:
					socketList[s] = select.kevent(s.fileno(), filter=select.KQ_FILTER_READ,
												flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE)
			s_readable = []
			s_writable = []
			s_writable.extend(x for x in wlist)
			s_exceptional = []
			for event in kq.control(socketList.values(), 100, timeout):
				sock = None
				for s, e in socketList.items():
					if e.ident == event.ident:
						sock = s
						break
				if event.filter == select.KQ_FILTER_READ:
					
					if event.flags & select.KQ_EV_ERROR or event.flags & select.KQ_EV_EOF:
						s_exceptional.append(sock)
						del socketList[sock]
					else:
						s_readable.append(sock)
						if event.flags != select.KQ_EV_ENABLE | select.KQ_EV_ADD:
							log.log(3, "unknow flags", bin(event.flags))
				else:
					log.log(3,"unknow filter",event.filter)
# 				if sock in s_writable:
# 					s_writable.remove(sock)
			return s_readable, s_writable, s_exceptional
		self.start(poll=kqueueProxy)
		
	def start(self, poll=select.select):
		while True:
			rlist = [] + self.serverList
			wlist = []
			allList = [] + self.serverList
			currentTime = time.time()
			
			for _, connect in self._socketConnectList.items():
				allList.append(connect._sock)
				if connect.info["lastAlive"] < currentTime - 1800:
					connect.shutdown()
					continue
				if connect.pauseSendAndRecv():
					continue
				rlist.append(connect._sock)
				if connect.getSendPending():
					wlist.append(connect._sock)
			try:
				s_readable, s_writable, s_exceptional = poll(rlist, wlist, allList, 1 if len(wlist) == 0 else 0.00001)
			except KeyboardInterrupt:
				break
			except:
				time.sleep(1)
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
					try:
						cbobj[0](*cbobj[2], **cbobj[3])
					except:
						log.log(3, cbobj)
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
		
		return {"connect":connects, "threads":sockConnect._connectPool.dump(), "currentTime":int(time.time())}

if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()
