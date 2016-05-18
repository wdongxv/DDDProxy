#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年11月18日

@author: dxw
'''
import struct
from DDDProxy.baseServer import sockConnect, socketBufferMaxLenght
import json
import hashlib
from DDDProxy import log



class symmetryConnect(sockConnect):
	"""
	@type remoteConnect: remoteServerConnect
	"""

	optCloseSymmetryConnect = -1

	optSymmetryPing = -2
	optSymmetryPingResponse = -3

	optCloseForceSymmetryConnect = -4

	
	def __init__(self,server):
		sockConnect.__init__(self, server)
		self.symmetryConnectId = 0
		self._symmetryConnectSendPendingCache = []
		self._requestRemove = False
		self.symmetryConnectManager = None
		self._symmetryPingLenght = 0
		
#--------

	def onRecv(self, data):
		sockConnect.onRecv(self, data)
		self.sendDataToSymmetryConnect(data)
		
		self._symmetryPingLenght += len(data)
		if(self._symmetryPingLenght>1024*1024*4):
			self._symmetryPingLenght = 0
			self.setIOEventFlags(sockConnect.socketIOEventFlagsNone)
			self.sendOptToSymmetryConnect(symmetryConnect.optSymmetryPing)
		
	def onClose(self):
		self.sendOptToSymmetryConnect(symmetryConnect.optCloseSymmetryConnect)
		self._requestRemove = True
	
#--------
	def onSymmetryConnectServerClose(self):
		self.close()
	def onSymmetryConnectData(self,data):
		pass
	def onSymmetryConnectOpt(self,opt):
		if opt == symmetryConnect.optCloseSymmetryConnect:
			self.close()
		elif opt == symmetryConnect.optSymmetryPing:
			self.sendOptToSymmetryConnect(symmetryConnect.optSymmetryPingResponse)
		elif opt == symmetryConnect.optSymmetryPingResponse:
			flags = sockConnect.socketIOEventFlagsRead
			if self.getSendPending():
				flags |= sockConnect.socketIOEventFlagsWrite
			self.setIOEventFlags(flags)
		elif opt == symmetryConnect.optCloseForceSymmetryConnect:
			self.shutdown()
			self.onClose()
			log.log(2,self,"<<< optCloseForceSymmetryConnect, close")
		
	def sendOptToSymmetryConnect(self,opt):
		if self._requestRemove:
			return
		optData = symmetryConnectServerHandler.optChunk(self.symmetryConnectId, opt)
		if type(optData) != str:
			raise "data not is str"
		self._symmetryConnectSendPendingCache.append(optData)
		self.requestSymmetryConnectManagerWrite()
	def sendDataToSymmetryConnect(self,data):
		if self._requestRemove:
			return
		if type(data) != str:
			raise "data not is str"
		for part in symmetryConnectServerHandler.dataChunk(self.symmetryConnectId, data):
			if type(part) != str:
				raise  "part not is str"
			self._symmetryConnectSendPendingCache.append(part)
		self.requestSymmetryConnectManagerWrite()
	def requestSymmetryConnectManagerWrite(self):
		if not self.symmetryConnectManager:
			pass
		else:
			self.symmetryConnectManager.send("")
#--------------- for symmetryConnectServerHandler
	def symmetryConnectSendPending(self):
		return len(self._symmetryConnectSendPendingCache)
	def getSymmetryConnectSendData(self):
		return self._symmetryConnectSendPendingCache.pop(0)
	def requestRemove(self):
		return self._requestRemove
	
class symmetryConnectServerHandler(sockConnect):

	serverToServerJsonMessageConnectId = -1
	
	def __init__(self, server, *args, **kwargs):
		sockConnect.__init__(self, server, *args, **kwargs)
		self.symmetryConnectList = {}
		self._symmetryConnectMessageBuffer = ""
		self.symmetryConnectIdLoop = 0
	
	def onSend(self, data):
		sockConnect.onSend(self, data)
	def getSendData(self, length):
		while sockConnect.getSendPending(self) <= socketBufferMaxLenght*2:
			found = False
			for symmetryConnectId,v in self.symmetryConnectList.items():
				if v.symmetryConnectSendPending():
					data = v.getSymmetryConnectSendData()
					found = True
					try:
						self.send(data)
					except:
						raise data,"is generator??"
				elif v.requestRemove():
					del self.symmetryConnectList[symmetryConnectId]
			if not found:
				break
		return sockConnect.getSendData(self, length)
# 		print "<onSend  ------\n",data,"\n--------->"

# -------------  

	def onServerToServerMessage(self,serverMessage):
		pass

# -------------		
	def onClose(self):
		for _,connect in self.symmetryConnectList.items():
			connect.onSymmetryConnectServerClose()

	@staticmethod
	def optChunk(symmetryConnectId,opt):
		if opt >=0:
			raise Exception("opt must < 0")
		return struct.pack("i", symmetryConnectId)+struct.pack("h", opt) +"\n"

	@staticmethod
	def dataChunk(symmetryConnectId,data):
		l = len(data)
		if l > 32767:  #分块
			for d in symmetryConnectServerHandler.dataChunk(symmetryConnectId, data[:32767]):
				yield d
			for d in symmetryConnectServerHandler.dataChunk(symmetryConnectId, data[32767:]):
				yield d
		else:
			yield struct.pack("i", symmetryConnectId)+struct.pack("h", l) +data+"\n"
	
	
	_headSize = struct.calcsize("ih")
	def onRecv(self,data):
		sockConnect.onRecv(self, data)
		self._symmetryConnectMessageBuffer += data
		while True:
			bufferLen = len(self._symmetryConnectMessageBuffer)
			_headSize = symmetryConnectServerHandler._headSize
			if bufferLen >= _headSize:
				symmetryConnectId,dataSize = struct.unpack("ih",self._symmetryConnectMessageBuffer[:_headSize])
				if dataSize>=0:
					endIndex = dataSize+_headSize
					if bufferLen > endIndex:
						dataMessage = self._symmetryConnectMessageBuffer[_headSize:endIndex]
						self._symmetryConnectMessageBuffer = self._symmetryConnectMessageBuffer[endIndex+1:]
						self._onRecvData(symmetryConnectId, dataMessage)
					else:
						break
				else:
					self._symmetryConnectMessageBuffer = self._symmetryConnectMessageBuffer[_headSize+1:]
					self._onRecvOpt(symmetryConnectId, dataSize)
			else:
				break
	
	def _onRecvData(self,symmetryConnectId,data):
# 		print "<_onRecvData ",symmetryConnectId," ----------\n",data,"\n------------->"
		if symmetryConnectId == symmetryConnectServerHandler.serverToServerJsonMessageConnectId:
			try:
				serverMessage = json.loads(data)
				self.onServerToServerMessage(serverMessage)
			except:
				pass
		else:
			connect = self.getSymmetryConnect(symmetryConnectId)
			if connect:
				connect.onSymmetryConnectData(data)

	def _onRecvOpt(self,symmetryConnectId,opt):
# 		print "<_onRecvOpt ",symmetryConnectId," ------",opt,"--------->"
		if symmetryConnectId == symmetryConnectServerHandler.serverToServerJsonMessageConnectId:
			pass
		else:
			connect = self.getSymmetryConnect(symmetryConnectId)
			if connect:
				connect.onSymmetryConnectOpt(opt)
	def getSymmetryConnect(self,symmetryConnectId):
		return self.symmetryConnectList[symmetryConnectId] if symmetryConnectId in self.symmetryConnectList else None
# -----------
	def sendOpt(self,symmetryConnectId,opt):
		self.send(self.optChunk(symmetryConnectId, opt))
	def sendData(self,symmetryConnectId,data):
		for d in self.dataChunk(symmetryConnectId, data):
			self.send(d)
	def addSymmetryConnect(self,connect,connectId):
		connect.symmetryConnectId = connectId
		connect.symmetryConnectManager = self
		self.symmetryConnectList[connectId] = connect
		
	def makeSymmetryConnectId(self):
		self.symmetryConnectIdLoop += 1
		return self.symmetryConnectIdLoop

	def authMake(self,auth,timenum):
		return {
			"time":timenum,
			"password":hashlib.md5("%s_%d" % (auth, timenum)).hexdigest()
			}
