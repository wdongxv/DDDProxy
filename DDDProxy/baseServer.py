# -*- coding: UTF-8 -*-
'''
Created on 2015年9月3日

@author: dxw
'''
from datetime import datetime
import json
import random
import socket
import ssl
import time
import os
import select

from . import log
from .ThreadPool import ThreadPool
from .log import cmp
from .version import version
from functools import cmp_to_key


import sys
import http
if sys.version[0] != '3':
	raise "not python 3"
socket.setdefaulttimeout(5)
socketBufferMaxLenght = 1024

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
					"recv":0,
# 					"lastSendTime":int(time.time()),
					"lastRecvTime":int(time.time()),
					}
		self._sock = None
		self.address = (None, None)
		self.addressIp = ""
		sockConnect._filenoLoop += 1
		self._fileno = sockConnect._filenoLoop
		self._sendPendingCache = b""
		self._requsetClose = False
		self._connecting = False
		self._ioEventFlags = sockConnect.socketIOEventFlagsNone
	def fileno(self):
		return self._fileno
	def onConnected(self):
		self.addIOEventFlags(sockConnect.socketIOEventFlagsRead)
		
	def onRecv(self, data):
		self.info["lastRecvTime"] = int(time.time())
		pass
	def onSend(self, data):
# 		self.info["lastSendTime"] = int(time.time())
		pass
	def onClose(self):
		pass
	def setIOEventFlags(self, flags):
# 		if flags == sockConnect.socketIOEventFlagsWrite:
# 			pass
		if self._ioEventFlags != flags and self._sock:
			self._ioEventFlags = flags
			self.server.onIOEventFlagsChanged(self)
	def unsetIOEventFlags(self, flags):
		self.setIOEventFlags(self._ioEventFlags & (0xffff ^ flags))
	def addIOEventFlags(self, flags):
		self.setIOEventFlags(self._ioEventFlags | flags)
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

		
	_connectPool = ThreadPool(maxThread=100)
	
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
		if len(self._sendPendingCache) == 0 and not self._requsetClose:
			self.unsetIOEventFlags(sockConnect.socketIOEventFlagsWrite)
		return data

# 	client operating
	def _initSocket(self,addr):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect(addr)
		return sock
	def connect(self, address, cb=None):
		if self.connectStatus():
			raise Exception(self, "connect status is", self.connectStatus())
		self._connecting = True
		self.address = address
		self.addressIp = ""
		def _doConnectSock(setThreadName=None):
			self._connecting = True
			addr = None
			sock = None
			error = None
			try:
				iplist = socket.gethostbyname_ex(address[0])[2]
				iplist.sort()
				addr = (random.choice(iplist), int(address[1]))
				threadName = "connect %s:%s" % (address[0], address[1])
				log.log(1, threadName)
				if setThreadName:
					setThreadName(threadName)
				if addr[0] != address[0]:
					self.addressIp = addr[0]
			
				sock = self._initSocket(addr)
				if not sock:
					error = "not sock"
			except Exception as e:
				error = str(e)
				log.log(2,"connecting", address, error)
			if not error:
				self.server.addCallback(self._setConnect, sock, address)
			else:
				self._connecting = False
				self.server.addCallback(self.onClose)
			if cb:
				self.server.addCallback(cb, error, self)
		sockConnect._connectPool.apply_async(_doConnectSock)
	def send(self, data):
		if self._requsetClose:
			return
		self._sendPendingCache += data
		self.addIOEventFlags(sockConnect.socketIOEventFlagsWrite)

	def close(self):
		if self._requsetClose:
			return
		self.send(b"")
		self._requsetClose = True
	
	def shutdown(self):
		if self.server.removeSocketConnect(self):
			sock = self._sock 
			def close():
				try:
					sock.close()
				except:
					pass
				self.server.addCallback(self.onClose)
			self._sock = None
			self.server.addDelay(1, close)
# 		self.close()
# 	for server
	def lastAlive(self):
		return self.info["lastRecvTime"]
	def _onReadyRecv(self):
		data = None
		
		try:
			data = self._sock.recv(socketBufferMaxLenght)
		except ssl.SSLError as e:
			if e.errno == 2:
				return
			log.log(2, self, str(e))
		except Exception as e:
			log.log(2, self, str(e))
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
			log.log(1, self, "<<< data is pool,close")
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
# 		log.log(1, self, "<<< request close")
		self.shutdown()
	def onSocketEvent(self, event):
		if event == sockConnect.socketEventCanRecv:
			self._onReadyRecv()
		elif event == sockConnect.socketEventCanSend:
			self._onReadySend()
		elif event == sockConnect.socketEventExcept:
			self.shutdown()
			log.log(2, self, "<<< socketEventExcept, close")
			
# 	for http
	def getFileContent(self, name,encoding="utf-8"):
		content = None
		try:
			with open(name,"rt",encoding=encoding) as f:
				content = f.read()
		except:
			log.log(3)
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
		if type(data) is dict or type(data) is list:
			try:
				data = json.dumps(data)
			except:
				log.log(3, data)
				data = "error"
			ContentType = "application/json"

		if type(data) is str:
			data = data.encode()
		httpMessage = ""
		try:
			httpStatus = http.HTTPStatus(code).phrase
		except:
			try:
				httpStatus = http.client.responses[code]
			except:
				httpStatus = "unknow"
		httpMessage += "HTTP/1.1 " + str(code) + " " + httpStatus + "\r\n"
		httpMessage += "Server: DDDProxy/%s\r\n"%(version)
		httpMessage += "Date: " + httpdate() + "\r\n"
		httpMessage += "Content-Length: " + str(len(data)) + "\r\n"
		httpMessage += "Content-Type: " + ContentType + "\r\n"
		httpMessage += "Connection: " + connection + "\r\n"
		for k, v in header.items():
			httpMessage += k + ": " + v + "\r\n"
		httpMessage += "\r\n"
		return httpMessage.encode() + data
	def reseponse(self, data, ContentType="text/html", code=200, connection="close", header={}):
		self.send(self.makeReseponse(data, ContentType, code, connection, header))
		if connection == "close":
			self.close()
# other 
	def addressStr(self):
		return "%s%s:%s"%(self.address[0],("("+self.addressIp +")") if self.addressIp != "" else "",self.address[1])
	def __str__(self, *args, **kwargs):
		return  self.filenoStr() + self.addressStr()
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
			log.log(1, connect, "*	connect")
class _baseServer():
	def __init__(self):
		self._socketConnectList = {}
		self.callbackList = []
		socket.setdefaulttimeout(10)

	def addCallback(self, cb, *args, **kwargs):
		self.callbackList.append((cb, 0, args, kwargs))
	def addDelay(self, delay, cb, *args, **kwargs):
		self.callbackList.append((cb, delay + time.time(), args, kwargs))
	def cancelCallback(self, cb):
		i = len(self.callbackList) - 1
		while i >= 0:
			c = self.callbackList[i][0]
			if c == cb:
				del self.callbackList[i]
			i -= 1
	def addListen(self, handler, port, host=""):
# 		self.server = bind_sockets(port=self.port, address=self.host) 
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		log.log(2,"start server on: " , host + ":" + str(port))
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
				connect.setIOEventFlags(0)
				del self._socketConnectList[k]
				return True
		return False
	def onIOEventFlagsChanged(self, connect):
		pass
	def start(self):
		raise "error"
	def _handlerCallback(self):
		currentTime = time.time()
		cblist = []
		cbDelaylist = []
		for cbobj in self.callbackList:
			if cbobj[1] <= currentTime:
				cblist.append(cbobj)
			else:
				cbDelaylist.append(cbobj)
		self.callbackList = cbDelaylist
		for cbobj in cblist:
			try:
				cbobj[0](*cbobj[2], **cbobj[3])
			except:
				log.log(3, cbobj)
		
		currentTime = time.time()
		for _, connect in self._socketConnectList.items():
			if isinstance(connect, sockServerConnect):
				continue
			if connect.lastAlive() < currentTime - 1800:
				self.addDelay(1, connect.shutdown)
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
			info = {"name":str(handler)}
			info.update(handler.info)
			connects[connect].append(info)
		def sort(x,y):
			return cmp(y["send"] + y["recv"], x["send"] + x["recv"])
		for k,v in connects.items():
			connects[k] = sorted(v,key=cmp_to_key(sort))
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
		return res
	def onIOEventFlagsChanged(self, connect):
		if connect._ioEventFlags & sockConnect.socketIOEventFlagsRead:
			if not connect._sock in self.rlist:
				self.rlist.append(connect._sock)
		elif connect._sock in self.rlist:
			self.rlist.remove(connect._sock)
			
		if connect._ioEventFlags & sockConnect.socketIOEventFlagsWrite:
			if not connect._sock in self.wlist:
				self.wlist.append(connect._sock)
		elif connect._sock in self.wlist:
			self.wlist.remove(connect._sock)

class kqueueBaseServer(_baseServer):
	def __init__(self):
		_baseServer.__init__(self)
		self.kq = select.kqueue()
	def addSockConnect(self, connect):
		res = _baseServer.addSockConnect(self, connect)
		if res:
			connect._ioEventFlags_keventSet = 0
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
	def onIOEventFlagsChanged(self, connect):
		if connect._ioEventFlags != sockConnect.socketIOEventFlagsNone:
			eventmask = select.EPOLLERR | select.EPOLLHUP
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
			eventList = self.epollor.poll(1, 1000)
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

baseServer = selectBaseServer
# if "kqueue" in select.__dict__:
# 	baseServer = kqueueBaseServer
# if "epoll" in select.__dict__:
# 	baseServer = epollBaseServer

if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()
