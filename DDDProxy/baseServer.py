# -*- coding: UTF-8 -*-
'''
Created on 2015年9月3日

@author: dxw
'''
import logging
import socket
import sys
import time
import traceback
import select

bufferSize = 1024
debuglevel = 2

class sockConnect(object):
	"""
	@type sock: _socketobject
	"""
	def __init__(self,server):
		self.server = server
		self.info = {
					"startTime":time.time()
					}
		self.sock = None
		self.address = (None,None)
		self.dataSendList = []
		self._fileno = None
	def __str__(self, *args, **kwargs):
		return ""+str(self.address)
	def connect(self,sock,address):
		"""
		@param address: 仅记录
		"""
		self.address = address
		self.sock = sock
		self.server.addSockConnect(self)
	def connectWithAddress(self,address):
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			addr = (socket.gethostbyname(address[0]),address[1])
			s.connect(addr)
			s.setblocking(0)
			self.connect(s, address)
			return True
		except:
			baseServer.log(3,address)
			self.server.addCallback(self.onClose)
		return False
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
		if len(data)>bufferSize:
			self.dataSendList.append(data[:bufferSize])
			self.send(data[bufferSize:])
		else:
			self.dataSendList.append(data)
	def onConnected(self):
		pass
	def onRecv(self,data):
		pass
	def onSend(self,data):
		self.sock.send(data)
	def onClose(self):
		pass
	def close(self):
		self.send(None)
class baseServer():
	def __init__(self,handler):
		self.handler = handler

		self.socketList = {}
		self.serverList = []

		self.callbackList = []
		self._filenoLoop = 0
		
	def addCallback(self,cb, *args, **kwargs):
		self.callbackList.append((cb,0,args,kwargs))
		
	def addListen(self,port,host=""):
# 		self.server = bind_sockets(port=self.port, address=self.host) 
		
		server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		server.bind((host, port))
		server.listen(1024)
		server.setblocking(0)

		self.serverList.append(server)
	def addSockListen(self,sock):
		sock.setblocking(0)
		self.serverList.append(sock)
		
	def addSockConnect(self,connect):
		if not connect.sock in self.socketList:
			self.socketList[connect.sock] = connect
			baseServer.log(2,connect,">	connect")
			
	def handleNewConnect(self,sock,address):
		self._filenoLoop += 1
		handler = self.handler(server=self)
		handler._fileno = self._filenoLoop
		self.socketList[sock] = handler
		handler._setConnect(sock, address)
		baseServer.log(2,handler,"*	connect")

	@staticmethod
	def log(level, *args, **kwargs):
		if level < debuglevel:
			return
		
		data = "	".join(str(i) for i in args)
		if level==3:
			data += "	"+str(sys.exc_info())
			data += "	"+str(traceback.format_exc())
		
		data = time.strftime("%y-%B-%d %H:%M:%S:	")+ data
		if level<2:
			print data+"\n"
		else:
			logging.log([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR][level], data)
	def start(self):
		while True:
			rlist = self.serverList + self.socketList.keys()
			wlist = []
			for connect in self.socketList.values():
				if len(connect.dataSendList)>0:
					wlist.append(connect.sock)
			readable,writable,exceptional = select.select(rlist, wlist, rlist,1)
			if readable:
				for sock in readable:
					if sock in self.serverList:
						self.onConnect(sock)
					else:
						self.onData(sock)
			if writable:
				for sock in writable:
					connect = self.socketList[sock]
					data = connect.dataSendList.pop(0)
					if data:
# 						baseServer.log(2,"onSend",sock.fileno(),connect,data)
						connect.onSend(data)
					else:
						sock.close()
						self.onExcept(sock)
			if exceptional:
				for sock in exceptional:
					self.onExcept(sock)
				
			cblist = self.callbackList
			self.callbackList = []
			while len(cblist):
				cbobj = cblist.pop(0)
				cbobj[0](*cbobj[2],**cbobj[3])
				
	def onConnect(self,sock):
		connect,address = sock.accept()
		connect.setblocking(0)
		self.handleNewConnect(connect,address)
		
	def onData(self,sock):
		data = sock.recv(bufferSize)
		if data:
			handler = self.socketList[sock]
# 			baseServer.log(2,"onData",sock.fileno(),handler)
			handler.onRecv(data)
		else:
			self.onExcept(sock)
	def onExcept(self,sock):
		if sock in self.socketList:
			handler = self.socketList[sock]
			baseServer.log(2,handler,"<	close")
			del self.socketList[sock]
			handler.onClose()
			
if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()
