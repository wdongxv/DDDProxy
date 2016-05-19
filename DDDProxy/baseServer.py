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

	
	socketEventCanRecv = 1
	socketEventCanSend = 2
	socketEventExcept = 4

	socketIOEventFlagsNone = 0
	socketIOEventFlagsRead = 1
	socketIOEventFlagsWrite = 2

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
		
		self._ioEventFlags = sockConnect.socketIOEventFlagsNone
	def fileno(self):
		return self._fileno
	def onConnected(self):
		self.setIOEventFlags(sockConnect.socketIOEventFlagsRead)
		
	def onRecv(self, data):
		pass
	def onSend(self, data):
		pass
	def onClose(self):
		pass
	def setIOEventFlags(self, flags):
		if not self._sock:
			return

		if flags == sockConnect.socketIOEventFlagsWrite:
			pass
		if self._ioEventFlags != flags:
			self._ioEventFlags = flags
			self.server.onIOEventFlagsChanged(self)
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
		certPath = self.SSLLocalCertPath(remoteServerHost, remoteServerPort)
		try:
			if not os.path.exists(certPath):
				cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerPort))
				f = open(certPath, "wt")
				f.write(cert)
				f.close()
			ok = True
		except:
			log.log(3, remoteServerHost, remoteServerPort)
		sockConnect._createCertLock.release()
		return ok
	def deleteRemoteCert(self, remoteServerHost, remoteServerPort):
		sockConnect._createCertLock.acquire()
		certPath = self.SSLLocalCertPath(remoteServerHost, remoteServerPort)
		if os.path.exists(certPath):
			os.unlink(certPath)
		sockConnect._createCertLock.release()
		
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
		except Exception as e:
			if str(e).find("handshake"):
				self.deleteRemoteCert(address[0], address[1])
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
		if not self._sendPendingCache and not self._requsetClose:
			self.setIOEventFlags(sockConnect.socketIOEventFlagsRead)
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
		self.setIOEventFlags(sockConnect.socketIOEventFlagsRead | sockConnect.socketIOEventFlagsWrite)

	def close(self):
		if self._requsetClose:
			return
		self.send("")
		self._requsetClose = True
		self.makeAlive()
	
	def shutdown(self):
		if self.server.removeSocketConnect(self):
			try:
				_sock.close()
			except:
				pass
			self.server.addCallback(self.onClose)
		
# 		self.close()
# 	for server

	def _onReadyRecv(self):
		data = None
		
		try:
			data = self._sock.recv(socketBufferMaxLenght)
		except ssl.SSLError as e:
			if e.errno == 2:
				return
			log.log(3, self)
		except:
			log.log(3, self)
		
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
		data = self.getSendData(socketBufferMaxLenght)
		if data:
			self.info["send"] += len(data)
			try:
				self._sock.send(data)
				self.onSend(data)
				return
			except:
				log.log(3)
		log.log(2, self, "<<< request close")
		self.shutdown()
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

class sockServerConnect(sockConnect):
	def __init__(self, handler, server):
		self.handler = handler
		sockConnect.__init__(self, server)
	def onSocketEvent(self, event):
		if event == sockConnect.socketEventCanRecv:
			sock, address = self._sock.accept()
			connect = self.handler(server=self.server)
			connect._setConnect(sock, address)
			log.log(2, connect, "*	connect")
class _baseServer():
	def __init__(self):
		self._socketConnectList = {}
		self.callbackList = []
		socket.setdefaulttimeout(10)

	def addCallback(self, cb, *args, **kwargs):
		self.callbackList.append((cb, 0, args, kwargs))
	def addDelay(self, delay, cb, *args, **kwargs):
		self.callbackList.append((cb, delay + time.time(), args, kwargs))
		
	def addListen(self, handler, port, host=""):
# 		self.server = bind_sockets(port=self.port, address=self.host) 
		log.log(1, "run in ", host, ":", port)
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		print "start server on: " + host + ":" + str(port)
		sock.bind((host, port))
		sock.listen(socketBufferMaxLenght)
		self.addSockListen(sock, handler)
	def addSockListen(self, sock, handler):
		"""
		@param sock: _socketobject
		"""
		connect = sockServerConnect(handler, self)
		connect._setConnect(sock, sock.getsockname())
		
# manager connect

	def addSockConnect(self, connect):
		if not connect._sock in self._socketConnectList:
			connect._sock.setblocking(False)
			self._socketConnectList[connect._sock.fileno()] = connect
			return True
		return False
	def removeSocketConnect(self, connect):
		for k, v in self._socketConnectList.items():
			if v == connect:
				del self._socketConnectList[k]
				return True
		return False
	def onIOEventFlagsChanged(self, connect):
		pass
	def start(self):
		raise "error"
	def _handlerCallback(self):
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
		
		currentTime = time.time()
		for _, connect in self._socketConnectList.items():
			if isinstance(connect, sockServerConnect):
				continue
			if connect.info["lastAlive"] < currentTime - 1800:
				connect.shutdown()
			
# 	for  sock event
	def onSocketEvent(self, sockfileno, event):
		
		if sockfileno in self._socketConnectList:
			connect = self._socketConnectList[sockfileno]
			connect.onSocketEvent(event)
		else:
			log.log(2, "sock not in self._socketConnectList:", sockfileno);
			return False
		return True
# other
	def dumpConnects(self):
		connects = {}
		for handler in self._socketConnectList.values():
			connect = handler.address[0]
			if not connect in connects:
				connects[connect] = []
			info = {"name":str(handler) + str(handler._ioEventFlags)}
			info.update(handler.info)
			connects[connect].append(info)
		
		for l in connects.values():
			l.sort(cmp=lambda x, y : cmp(y["send"] + y["recv"], x["send"] + x["recv"]))
		
		return {"connect":connects, "threads":sockConnect._connectPool.dump(), "currentTime":int(time.time())}

class selectBaseServer(_baseServer):
	def __init__(self):
		_baseServer.__init__(self)
		self.rlist = []
		self.wlist = []
		self.allList = [] 
		
	def start(self):
		while True:
			try:
				s_readable, s_writable, s_exceptional = select.select(self.rlist, self.wlist, self.allList, 0.5)
			except KeyboardInterrupt:
				break
			except:
				time.sleep(1)
				log.log(3)
				continue;
			for sock in s_readable:
				self.onSocketEvent(sock.fileno(), sockConnect.socketEventCanRecv)
			for sock in s_writable:
				self.onSocketEvent(sock.fileno(), sockConnect.socketEventCanSend)
			for sock in s_exceptional:
				self.onSocketEvent(sock.fileno(), sockConnect.socketEventExcept)
			self._handlerCallback()
	def addSockConnect(self, connect):
		res = _baseServer.addSockConnect(self, connect)
		if res:
			self.allList.append(connect._sock)
		return res
	def removeSocketConnect(self, connect):
		res = _baseServer.removeSocketConnect(self, connect)
		if res:
			self.allList.remove(connect._sock)
			connect.setIOEventFlags(0)
		return res
	def onIOEventFlagsChanged(self, connect):
		if connect._ioEventFlags & sockConnect.socketIOEventFlagsRead:
			if not connect._sock in self.rlist:
				self.rlist.append(connect._sock)
		elif connect._sock in self.rlist:
			del self.rlist[connect._sock]
			
		if connect._ioEventFlags & sockConnect.socketIOEventFlagsWrite:
			if not connect._sock in self.rlist:
				self.wlist.append(connect._sock)
		elif connect._sock in self.rlist:
			del self.wlist[connect._sock]

class kqueueBaseServer(_baseServer):
	def __init__(self):
		_baseServer.__init__(self)
		self.kq = select.kqueue()
	def addSockConnect(self, connect):
		res = _baseServer.addSockConnect(self, connect)
		if res:
			connect._ioEventFlags_keventSet = 0
		return res
	def removeSocketConnect(self, connect):
		res = _baseServer.removeSocketConnect(self, connect)
		if res:
			connect.setIOEventFlags(0)
		return res
	def onIOEventFlagsChanged(self, connect):
		fileno = connect._sock.fileno()
		changed = connect._ioEventFlags_keventSet ^ connect._ioEventFlags
		if changed & sockConnect.socketIOEventFlagsRead:
			flags = select.KQ_EV_ADD if (connect._ioEventFlags & sockConnect.socketIOEventFlagsRead) else select.KQ_EV_DELETE
			self.kq.control([select.kevent(fileno, filter=select.KQ_FILTER_READ,
												flags=flags)], 0)
# 			print connect,"KQ_FILTER_READ",flags
		if changed & sockConnect.socketIOEventFlagsWrite:
			flags = select.KQ_EV_ADD if (connect._ioEventFlags & sockConnect.socketIOEventFlagsWrite) else select.KQ_EV_DELETE
			self.kq.control([select.kevent(fileno, filter=select.KQ_FILTER_WRITE,
												flags=flags)], 0)
# 			print connect,"KQ_FILTER_WRITE",flags
		connect._ioEventFlags_keventSet = connect._ioEventFlags
		
	def start(self):
		while True:
			eventlist = self.kq.control(None, 100, 1)
			for event in eventlist:
				send = True
				if event.flags & select.KQ_EV_ERROR:
					send = self.onSocketEvent(event.ident, sockConnect.socketEventExcept)
				elif event.filter == select.KQ_FILTER_READ:
					send = self.onSocketEvent(event.ident, sockConnect.socketEventCanRecv)
				elif event.filter == select.KQ_FILTER_WRITE:
					if event.flags & select.KQ_EV_EOF:
						send = self.onSocketEvent(event.ident, sockConnect.socketEventExcept)
					else:
						send = self.onSocketEvent(event.ident, sockConnect.socketEventCanSend)
				if not send:
					try:
						self.kq.control([select.kevent(event.ident, filter=select.KQ_FILTER_WRITE,
												flags=select.KQ_EV_DELETE)], 0)
					except:
						pass
					try:
						self.kq.control([select.kevent(event.ident, filter=select.KQ_FILTER_READ,
												flags=select.KQ_EV_DELETE)], 0)
					except:
						pass
			self._handlerCallback()
class epollBaseServer(_baseServer):
	def __init__(self):
		_baseServer.__init__(self)
		self.epollor = select.epoll()
	def addSockConnect(self, connect):
		res = _baseServer.addSockConnect(self, connect)
		if res:
			connect.registerEpoll = False
		return res
	def removeSocketConnect(self, connect):
		res = _baseServer.removeSocketConnect(self, connect)
		if res:
			connect.setIOEventFlags(0)
		return res
	def onIOEventFlagsChanged(self, connect):
		if connect._ioEventFlags != sockConnect.socketIOEventFlagsNone:
			eventmask = 0
			if connect._ioEventFlags & sockConnect.socketIOEventFlagsRead:
				eventmask |= select.EPOLLIN
			if connect._ioEventFlags & sockConnect.socketIOEventFlagsWrite:
				eventmask |= select.EPOLLOUT
			if not connect.registerEpoll:
				self.epollor.register(connect._sock.fileno(), eventmask)
				connect.registerEpoll = True
			else:
				self.epollor.modify(connect._sock.fileno(), eventmask)
		else:
			self.epollor.unregister(connect._sock.fileno())
			connect.registerEpoll = False
		
	def start(self):
		while True:
			eventList = self.epollor.poll(1,1000)
			for fd, event in eventList:
				if select.EPOLLIN & event:
					self.onSocketEvent(fd, sockConnect.socketEventCanRecv)
				elif select.EPOLLOUT & event:
					self.onSocketEvent(fd, sockConnect.socketEventCanSend)
				elif select.EPOLLERR & event or select.EPOLLHUP & event:
					self.onSocketEvent(fd, sockConnect.socketEventExcept)
				else:
					log.log(3, "unknow event", event) 

			self._handlerCallback()
baseServer = _baseServer
if "kqueue" in select.__dict__:
	baseServer = kqueueBaseServer
if "epoll" in select.__dict__:
	baseServer = epollBaseServer

if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()
