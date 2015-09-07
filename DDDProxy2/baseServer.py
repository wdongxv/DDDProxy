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
	def _setConnect(self,sock,address):
		"""
		@type sock: _socketobject
		"""
		self.sock = sock
		self.address = address
		print address,"connected"
		self.onConnected()
	
	def send(self,data):
		self.dataSendList.append(data)
	def onConnected(self):
		pass
	def onRecv(self,data):
		print self.address,"onRecv",data
		pass
	def onSend(self,data):
		print self.address,"onSend"
		self.sock.send(data)
	def onClose(self):
		print self.address,"onClose"
		pass
	def close(self):
		self.send(None)
class baseServer():
	def __init__(self,handler):
		self.handler = handler

		self.socketList = {}
		self.serverList = []
		
	def addListen(self,port,host=""):
# 		self.server = bind_sockets(port=self.port, address=self.host) 
		
		server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		server.bind((host, port))
		server.listen(1024)
		server.setblocking(0)
		

		self.serverList.append(server)
		
	def handleNewConnect(self,connect,address):
		"""
		
		"""
		
		handler = self.handler(server=self)
		self.socketList[connect] = handler
		handler._setConnect(connect, address)

	@staticmethod
	def log(level, *args, **kwargs):
		if level < debuglevel:
			return
		
		data = "	".join(str(i) for i in args)
		if level==3:
			data += "	"+str(sys.exc_info())
			data += "	"+str(traceback.format_exc())
		
		data = time.strftime("%y-%B-%d %H:%M:%S:	")+ data
		logging.log([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR][level], data)
	def start(self):
		while True:
			rlist = self.serverList + self.socketList.keys()
			wlist = []
			for connect in self.socketList.values():
				if len(connect.dataSendList)>0:
					wlist.append(connect.sock)
			readable,writable,exceptional = select.select(rlist, wlist, rlist,1)
			if not (readable or writable or exceptional) :
				continue
			
			for sock in readable:
				if sock in self.serverList:
					self.onConnect(sock)
				else:
					self.onData(sock)
			for sock in writable:
				connect = self.socketList[sock]
				data = connect.dataSendList.pop()
				if data:
					connect.onSend(data)
				else:
					sock.close()
					self.onExcept(sock)
				
			for sock in exceptional:
				self.onExcept(sock)
	def onConnect(self,sock):
		connect,address = sock.accept()
		connect.setblocking(0)
		self.handleNewConnect(connect,address)
		
	def onData(self,sock):
		data = sock.recv(1024)
		if data:
			self.socketList[sock].onRecv(data)
		else:
			self.onExcept(sock)
	def onExcept(self,sock):
		if sock in self.socketList:
			self.socketList[sock].onClose()
			del self.socketList[sock]
			
if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()

# 	def startNewThread(self, conn, addr, threadid):
# 		hand = None
# 		try:
# 			hand = self.handler(conn, addr, threadid)
# 			self.theadList.append(hand)
# 			hand.run()
# 		except:
# 			self.log(3)
# 			try:
# 				hand.close()
# 			except:
# 				pass
# 		if not hand is None:
# 			self.theadList.remove(hand)
# 		
# 	def exratInfo(self):
# 		return "";
# 
# 
# 	def theardCloseManger(self):
# 		threading.currentThread().name = "threadIDLECloseManager"
# 		while True:
# 			for hand in self.theadList:
# 				hand.requestClose()
# 			if len(mainThreadPool.waiters) > 10:
# 				mainThreadPool.stopAWorker()
# 			time.sleep(10);
# 	def serverListenStart(self):
# 		self.log(2, "Server Proess start!")
# 		threading.currentThread().name = "socketServerThread"
# 		threadid = 0
# 		while True:
# 			try:
# 				conn, addr = self.server.accept()  
# 				threadid += 1
# 				mainThreadPool.callInThread(self.startNewThread, conn, addr, threadid)
# # 				thread.start_new_thread(self.startNewThread, (conn, addr, threadid))  
# 			except KeyboardInterrupt:
# 				break
# 			except:
# 				self.log(3)
# 				time.sleep(1)
# 		self.log(2, "proess end!")
# 	def close(self):
# 		try:
# 			self.server.close()
# 		except:
# 			pass
# 		self.server = None
# 	def start(self,inThread=False):
# 		time.sleep(2)
# 		mainThreadPool.callInThread(self.theardCloseManger)
# # 		thread.start_new_thread(self.theardCloseManger, tuple())  
# 		if inThread:
# 			mainThreadPool.callInThread(self.serverListenStart)
# # 			thread.start_new_thread(self.serverListenStart, tuple())
# 		else:
# 			self.serverListenStart()