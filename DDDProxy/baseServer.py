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



createCertLock = threading.RLock()
socket.setdefaulttimeout(5)

class sockConnect(object):
	"""
	@type sock: _socketobject
	"""
	
	_filenoLoop = 0
	
	def __init__(self,server):
		self.server = server
		self.info = {
					"startTime":int(time.time()),
					"send":0,
					"recv":0
					}
		self.makeAlive()
		self.sock = None
		self.address = (None,None)
		self.dataSendList = []
		sockConnect._filenoLoop+=1
		self._fileno = sockConnect._filenoLoop
		self.connectName = ""
	def makeAlive(self):
		self.info["lastAlive"] = int(time.time())
		
	def __str__(self, *args, **kwargs):
		return self.connectName if self.connectName else  ( self.filenoStr()+str(self.address))
	def filenoStr(self):
		return "["+str(self.fileno())+"]"
	
	def SSLLocalCertPath(self,remoteServerHost,remoteServerPort):
		return configFile.makeConfigFilePathName("%s-%d.pem"%(remoteServerHost,remoteServerPort))

	def fetchRemoteCert(self,remoteServerHost,remoteServerPort):
		ok = False
		createCertLock.acquire()
		try:
			if not os.path.exists(self.SSLLocalCertPath(remoteServerHost,remoteServerPort)):
				cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerPort))
				open(self.SSLLocalCertPath(remoteServerHost,remoteServerPort), "wt").write(cert)
			ok = True
		except:
			log.log(3,remoteServerHost,remoteServerPort)
		createCertLock.release()
		return ok
	def _doConnectSock(self,address,useSsl=False,cb=None):
		ok = True
		try:
			sock = None
			addr = (socket.gethostbyname(address[0]),address[1])
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
			log.log(3,address)
			ok = False
		if ok:
			self.server.addCallback(self._setConnect,sock,address)
		else:
			self.server.addCallback(self.onClose)
		if cb:
			self.server.addCallback(cb,self if ok else None)
	connectPool = ThreadPool()
	def connect(self,address,useSsl=False,cb=None):
		"""
		@param address: 仅记录
		"""
		address = address
		sockConnect.connectPool.apply_async(self._doConnectSock,address,useSsl,cb)
# 		thread.start_new_thread(self._doConnectSock,())
	def _setConnect(self,sock,address):
		"""
		@type sock: _socketobject
		"""
		self.sock = sock
		self.address = address
		self.onConnected()
	
	def fileno(self):
		return self._fileno
	def send(self,data):
		if data and len(data)>1024:
			self.dataSendList.append(data[:1024])
			self.send(data[1024:])
		else:
			self.dataSendList.append(data)
	def onConnected(self):
		self.server.addSockConnect(self)
		
	def onRecv(self,data):
# 		log.log(2,self,"<<",repr(data))
		self.info["recv"] += len(data)
		self.makeAlive()
		
	def onSend(self,data):
		self.info["send"] += len(data)
		l = self.sock.send(data)
# 		log.log(2,self,">>",len(data),l)
		self.makeAlive()
	def onClose(self):
		pass
	def close(self):
		self.send(None)
class baseServer():
	def __init__(self,handler):
		self.handler = handler

		self._socketConnectList = {}
		self.serverList = []

		self.callbackList = []

		socket.setdefaulttimeout(10)

	def addCallback(self,cb, *args, **kwargs):
		self.callbackList.append((cb,0,args,kwargs))
	def addDelay(self,delay,cb, *args, **kwargs):
		self.callbackList.append((cb,delay+time.time(),args,kwargs))
		
	def addListen(self,port,host=""):
# 		self.server = bind_sockets(port=self.port, address=self.host) 
		log.log(1,"run in ",host,":",port)
		server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		
		server.bind((host, port))
		server.listen(1024)
		self.addSockListen(server)
	def addSockListen(self,sock):
		"""
		@param sock: _socketobject
		"""
		sock.setblocking(False)
		self.serverList.append(sock)
		
	def addSockConnect(self,connect):
		if not connect.sock in self._socketConnectList:
			connect.sock.setblocking(False)
			connect.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
			connect.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
			connect.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
			TCP_KEEPALIVE = 0x10
			connect.sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 3)
			self._socketConnectList[connect.sock] = connect
	

	def start(self):
		
		while True:
			rlist = self.serverList + self._socketConnectList.keys()
			wlist = []
			currentTime = time.time()
			for connect in self._socketConnectList.values():
				if len(connect.dataSendList)>0:
					wlist.append(connect.sock)
				elif connect.info["lastAlive"] < currentTime-3600:
					connect.close()
				
			try:
				s_readable,s_writable,s_exceptional = select.select(rlist, wlist, rlist,10)
			except:
				log.log(3)
				continue;
			timeCheck = []
			timeCheck.append(("start",time.time()))
			for sock in s_readable:
				if sock in self.serverList:
					self.onConnect(sock)
				else:
					self.onData(sock)
					timeCheck.append(("read",time.time(),sock))
			for sock in s_writable:
				self.onSend(sock)
				timeCheck.append(("write",time.time(),sock))
			for sock in s_exceptional:
				self.onExcept(sock)
				timeCheck.append(("except",time.time(),sock))
				
			cblist = self.callbackList
			self.callbackList = []
			currentTime = time.time()
			for cbobj in cblist:
				if cbobj[1] <= currentTime:
					cbobj[0](*cbobj[2],**cbobj[3])
				else:
					self.callbackList.append(cbobj)
				timeCheck.append(("callback",time.time(),cbobj))
			
			lastCheck = None
			for check in timeCheck:
				if lastCheck:
					usetime = check[1] - lastCheck[1]
					if usetime >1:
						log.log(3,check[0],"usetime > 1.0s",usetime,check[2])
				lastCheck = check
	def onConnect(self,sock):
		sock,address = sock.accept()
		connect = self.handler(server=self)
		connect._setConnect(sock, address)
		log.log(2,connect,"*	connect")
		
	def onSend(self,sock):
		if sock in self._socketConnectList:
			connect = self._socketConnectList[sock]
			data = connect.dataSendList.pop(0)
			if data:
				try:
					connect.onSend(data)
					return
				except:
					log.log(3)
			sock.close()
			self.onExcept(sock)
			
	def onData(self,sock):
		
		data = None
		
		try:
			data = sock.recv(1024)
		except ssl.SSLError as e:
			if e.errno == 2:
				return
			log.log(3)
		except:
			log.log(3)
		
		
		if isinstance(sock, ssl.SSLSocket):
			while 1:
				data_left = sock.pending()
				if data_left:
					data += sock.recv(data_left)
				else:
					break
		
		if data:
			if sock in self._socketConnectList:
				handler = self._socketConnectList[sock]
				handler.onRecv(data)
		else:
			self.onExcept(sock)
	def onExcept(self,sock):
		if sock in self._socketConnectList:
			handler = self._socketConnectList[sock]
			log.log(2,handler,"<	close")
			del self._socketConnectList[sock]
			handler.onClose()
			
if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()
