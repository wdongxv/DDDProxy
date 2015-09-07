#!/usr/bin/env python
# -*- coding: utf-8 -*-
import hashlib
import math
import struct
import time

from tornado.iostream import IOStream

from baseServer import baseServer
from tornado.ioloop import IOLoop
from DDDProxy2.baseServer import sockConnect


class messageHandler:
	_headSize = struct.calcsize("iH")
	def __init__(self):
		self.buffer = ""
	def onMessage(self,connectId,data):
		raise NotImplementedError()
	def onOpt(self,connectId,opt):
		raise NotImplementedError()
	def appendData(self, data):
		self.buffer += data
		while True:
			bufferLen = len(self.buffer)
			_headSize = messageHandler._headSize
			if bufferLen >= _headSize:
				connectId,dataSize = struct.unpack("ih",self.buffer[:_headSize])
				if dataSize>0:
					endIndex = dataSize+_headSize
					if bufferLen > endIndex:
						dataMessage = self.buffer[_headSize:endIndex]
						self.buffer = self.buffer[endIndex+1:]
						self.onMessage(connectId, dataMessage)
				else:
					self.buffer = self.buffer[_headSize+1:]
					self.onOpt(connectId, dataSize)
			else:
				break	
	
	def optChunk(self,connectId,opt):
		return struct.pack("i", connectId)+struct.pack("h", opt) +"\n"
	
	def dataChunk(self,connectId,data):
		l = len(data)
		if l > 32767:  #分块
			yield self.sendData(connectId, data[:32767])
			yield self.sendData(connectId, data[32767:])
		else:
			yield struct.pack("i", connectId)+struct.pack("h", l) +data+"\n"
		
class realConnect():
	def __init__(self,connectId):
		self.connectId = connectId
	def onMessage(self,data):
		pass

	
class remoteConnectServerHandler(sockConnect,messageHandler):  
	
	def __init__(self, *args, **kwargs):
		sockConnect.__init__(self, *args, **kwargs)
		messageHandler.__init__(self)
	def onMessage(self,connectId,data):
		if connectId == -1:
			pass
		print connectId,data
	def onOpt(self,connectId,opt):
		pass
	
	def onRecv(self,data):
		self.appendData(data)
		
class remoteServerConnect(IOStream,messageHandler):
	def __init__(self, socket, *args, **kwargs):
		IOStream.__init__(self, socket, *args, **kwargs)
		messageHandler.__init__(self)
		self.authPass = False
		self.read_until_close(None,self.onDataRevc)
		self.sendChunkList = []
	def auth(self,auth):
		randomNum = math.floor(time.time())
		self.send(-1,struct.pack("i", randomNum)+hashlib.md5("%s%d" % (auth, randomNum)).hexdigest())
		
	def onMessage(self,connectId,data):
		raise NotImplementedError()
	def onOpt(self,connectId,opt):
		raise NotImplementedError()
	
		
	def send(self,connectId,data):
		for d in self.dataChunk(connectId, data):
			self.write(d)
			
	def onDataRevc(self,data):
		self.appendData(data)

if __name__ == "__main__":
	server = baseServer(handler=remoteConnectServerHandler, port=8888)
	IOLoop.instance().start()
