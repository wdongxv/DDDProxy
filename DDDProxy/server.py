import socket
import DDDProxyConfig
import time
import logging
import sys
import traceback
import thread
import struct
import threading
from DDDProxyConfig import mainThreadPool
class baseServer(object):
	def __init__(self, host, port, handler):
		self.host = host
		self.port = port
		self.handler = handler
		self.server = None
		self.conn()
		self.theadList = list()
	def conn(self):
		if not self.server is None:
			return
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		self.server.bind((self.host, self.port))
		self.server.listen(1024)  
	@staticmethod
	def log(level, *args, **kwargs):
		if level < DDDProxyConfig.debuglevel:
			return
		
		data = "	".join(str(i) for i in args)
		if level==3:
			data += "	"+str(sys.exc_info())
			data += "	"+str(traceback.format_exc())
		
		data = time.strftime("%y-%B-%d %H:%M:%S:	")+ data
# 		print data
		logging.log([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR][level], data)
	def startNewThread(self, conn, addr, threadid):
		hand = None
		try:
			hand = self.handler(conn, addr, threadid)
			self.theadList.append(hand)
			hand.run()
		except:
			self.log(3)
			try:
				hand.close()
			except:
				pass
		if not hand is None:
			self.theadList.remove(hand)
		
	def exratInfo(self):
		return "";


	def theardCloseManger(self):
		threading.currentThread().name = "threadIDLECloseManager"
		while True:
			for hand in self.theadList:
				hand.requestClose()
			if len(mainThreadPool.waiters) > 10:
				mainThreadPool.stopAWorker()
			time.sleep(10);
	def serverListenStart(self):
		self.log(2, "Server Proess start!")
		threading.currentThread().name = "socketServerThread"
		threadid = 0
		while True:
			try:
				conn, addr = self.server.accept()  
				threadid += 1
				mainThreadPool.callInThread(self.startNewThread, conn, addr, threadid)
# 				thread.start_new_thread(self.startNewThread, (conn, addr, threadid))  
			except KeyboardInterrupt:
				break
			except:
				self.log(3)
				time.sleep(1)
		self.log(2, "proess end!")
	def close(self):
		try:
			self.server.close()
		except:
			pass
		self.server = None
	def start(self,inThread=False):
		time.sleep(2)
		
		mainThreadPool.callInThread(self.theardCloseManger)
# 		thread.start_new_thread(self.theardCloseManger, tuple())  
		if inThread:
			mainThreadPool.callInThread(self.serverListenStart)
# 			thread.start_new_thread(self.serverListenStart, tuple())
		else:
			self.serverListenStart()
class DDDProxySocketMessage:
	@staticmethod
	def send(conn,data):
		compressed = data#zlib.compress(data)
		dataLength = len(compressed)
		dataLengthPack = struct.pack("!i",dataLength)
		conn.send(dataLengthPack+compressed)
	@staticmethod
	def recv(conn):
		while True:
			dataLenPack = ""
			while len(dataLenPack)!=4:
				pack = conn.recv(4-len(dataLenPack));
				if not pack:
					return
				dataLenPack += pack
			
			dataLen = struct.unpack("!i",dataLenPack)[0]
			if dataLen == -1:
				break;
			compressed = ""
			while dataLen != len(compressed):
				pack = conn.recv(dataLen-len(compressed));
				if not pack:
					return
				compressed += pack
			decompress = compressed#zlib.decompress(compressed)
			yield decompress
	@staticmethod
	def end(conn):
		conn.send(struct.pack("!i",-1))
	@staticmethod
	def sendOne(conn,data):
		DDDProxySocketMessage.send(conn, data)
		DDDProxySocketMessage.end(conn)
	@staticmethod
	def recvOne(conn):
		value = ""
		for data in DDDProxySocketMessage.recv(conn):
			value += data
		return value;
class ServerHandler(object):
	def __init__(self,conn,addr,threadid):
		self.conn = conn
		self.startTime = time.time()
		self.lastActiveTime = time.time()
		self.lastActivePosition	=	""
		self.threadid	=	threadid
		self.addr		=	addr[0]
	def info(self):
		return "%d	[%s,%ds,%ds]"%(self.threadid,self.addr,time.time()-self.startTime,time.time()-self.lastActiveTime);
	def markActive(self,lastActivePosition=None):
		self.lastActiveTime = time.time()
		if lastActivePosition:
			self.lastActivePosition = lastActivePosition
	def close(self):
		try:
			if not self.conn is None:
				self.conn.shutdown(0)
		except:
			pass
		self.conn = None
	def requestClose(self):
		if time.time() - self.lastActiveTime > DDDProxyConfig.timeout:
			self.close();
