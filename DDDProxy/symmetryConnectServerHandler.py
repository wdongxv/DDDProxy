#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年11月18日

@author: dxw
'''
import struct
from DDDProxy.baseServer import sockConnect, socketBufferMaxLenght
import json
from DDDProxy import log
import time
from crypto.Cipher import AES

class symmetryConnect(sockConnect):
	"""
	@type remoteConnect: remoteServerConnect
	"""
	optCloseSymmetryConnect = -1
	optCloseForceSymmetryConnect = -4

	def __init__(self, server):
		sockConnect.__init__(self, server)
		self.symmetryConnectId = 0
		self._symmetryConnectSendPendingCache = []
		self._requestRemove = False
		self.symmetryConnectManager = None
		self._pauseRecv = False
#--------

	def onRecv(self, data):
		sockConnect.onRecv(self, data)
		self.sendDataToSymmetryConnect(data)
		
	def close(self):
		self._requestRemove = True
		sockConnect.close(self)
	
	def onClose(self):
		if not self._requestRemove:
			self.sendOptToSymmetryConnect(symmetryConnect.optCloseSymmetryConnect)
		self._requestRemove = True
		sockConnect.onClose(self)
	
#--------
	def onSymmetryConnectServerClose(self):
		self._requestRemove = True
		self.close()

	def onSymmetryConnectData(self, data):
		pass

	def onSymmetryConnectOpt(self, opt):
		if opt == symmetryConnect.optCloseSymmetryConnect:
			self.close()
		elif opt == symmetryConnect.optCloseForceSymmetryConnect:
			self.shutdown()
		
	def sendOptToSymmetryConnect(self, opt):
		addData = False
		if not self._requestRemove:
			self._symmetryConnectSendPendingCache.append(opt)
			addData = True
		if addData:
			self.requestSymmetryConnectManagerWrite()
		else:
			pass

	def sendDataToSymmetryConnect(self, data):
		addData = False
		if not self._requestRemove:
			self._symmetryConnectSendPendingCache.append(data)
			addData = True
			if len(self._symmetryConnectSendPendingCache) > 100 and not self._pauseRecv:
				self._pauseRecv = True
				self.setIOEventFlags(0)
		if addData:
			self.requestSymmetryConnectManagerWrite()
		else:
			pass

	def requestSymmetryConnectManagerWrite(self):
		if self.symmetryConnectSendPending():
			if not self.symmetryConnectManager:
				pass
			else:
				self.symmetryConnectManager.send("")

#--------------- for symmetryConnectServerHandler
	def symmetryConnectSendPending(self):
		return len(self._symmetryConnectSendPendingCache)

	def getSymmetryConnectSendData(self):
		sendData = ""
		sendOpt = ""
		while len(self._symmetryConnectSendPendingCache) > 0 and len(sendData) < 1024 * 8:
			data = self._symmetryConnectSendPendingCache.pop(0)
			if type(data) == str:
				sendData += data;
			elif type(data) == int:
				sendOpt = self.symmetryConnectManager.optChunk(self.symmetryConnectId, data)
				break
		if self._pauseRecv and len(self._symmetryConnectSendPendingCache) < 100:
			flags = sockConnect.socketIOEventFlagsRead
			if self.getSendPending():
				flags |= sockConnect.socketIOEventFlagsWrite
			self.setIOEventFlags(flags)
			self._pauseRecv = False
		data = ""
		if sendData:
			for part in self.symmetryConnectManager.dataChunk(self.symmetryConnectId, sendData):
				data += part
		return data + sendOpt

	def requestRemove(self):
		return self._requestRemove

	
class symmetryConnectServerHandler(sockConnect):

	serverToServerJsonMessageConnectId = -1
	serverToSymmetryConnectJsonMessageConnectId = -2
	
	def __init__(self, server, auth, *args, **kwargs):
		sockConnect.__init__(self, server, *args, **kwargs)
		self.symmetryConnectList = {}
		self._symmetryConnectMessageBuffer = ""
		self.symmetryConnectIdLoop = 0
		self.slowConnectStatus = False
		self._connectIsLive = True
		self._forcePing = 0
		self.info["pingSpeed"] = 0
		self.aes = AES.new(auth)

	def onConnected(self):
		sockConnect.onConnected(self)
		self.sendPingSpeedResponse()
		log.log(2, self, "onConnected")

	def onSend(self, data):
		sockConnect.onSend(self, data)

	def getSendData(self, length):
		while sockConnect.getSendPending(self) <= socketBufferMaxLenght * 2:
			found = False
			for symmetryConnectId, v in self.symmetryConnectList.items():
				if v.symmetryConnectSendPending():
					data = v.getSymmetryConnectSendData()
					found = True
					try:
						self.send(data)
					except:
						raise Exception(data, "is generator??")
				elif v.requestRemove():
					del self.symmetryConnectList[symmetryConnectId]
					if len(self.symmetryConnectList) == 0:
						self.server.addDelay(30, self.requestIdleClose)
						
			if not found:
				break
			
		data = sockConnect.getSendData(self, length)
		if not data and not self._requsetClose:
			log.log(2, "not data")
		return data

	def requestIdleClose(self):
		if len(self.symmetryConnectList) == 0:
			self.close()

	def requestSlowClose(self):
		log.log(2, self, "very slow , close")
		self.close()
			
	def onServerToServerMessage(self, serverMessage):
		opt = serverMessage["opt"] if "opt" in  serverMessage else ""
		if opt == "pingSpeed":
			serverMessage["opt"] = "pingSpeedResponse"
			self.sendData(symmetryConnectServerHandler.serverToServerJsonMessageConnectId,
						 json.dumps(serverMessage))
		elif opt == "pingSpeedResponse":
			useTime = time.time() - serverMessage["time"]
			self.info["lastPingSendTime"] = serverMessage["time"]
			self.info["pingSpeed"] = useTime
# 			log.log(2, self, "recv pingSpeedResponse", useTime)
			self.server.cancelCallback(self.setStatusSlow)
			self.server.cancelCallback(self.requestSlowClose)
			self.server.addDelay(30, self.sendPingSpeedResponse)

	def sendPingSpeedResponse(self):
		if self._connectIsLive and self._forcePing < 10 and self.info["pingSpeed"] != 0:
# 			log.log(2, self, "is live")
			self.server.addDelay(5, self.sendPingSpeedResponse)
			self._forcePing += 1
		else:
			self._forcePing = 0
# 			log.log(2, self, "unknow live status , ping...")
			data = {
				"opt":"pingSpeed",
				"time":time.time()
			}
			self.sendData(symmetryConnectServerHandler.serverToServerJsonMessageConnectId,
						 json.dumps(data))
			self.server.addDelay(5, self.setStatusSlow)
			self.server.addDelay(60 * 2, self.requestSlowClose)
		self._connectIsLive = False
		
	def setStatusSlow(self):
		self.slowConnectStatus = True
		self.info["slowConnectStatus"] = True

	def onClose(self):
		self.server.cancelCallback(self.sendPingSpeedResponse)
		self.server.cancelCallback(self.setStatusSlow)
		self.server.cancelCallback(self.requestSlowClose)
		for _, connect in self.symmetryConnectList.items():
			connect.onSymmetryConnectServerClose()
		log.log(2, self, "onClose")

	_headSize = struct.calcsize("ih")
	
	def optChunk(self,symmetryConnectId, opt):
		data = ""
		for d in self.dataChunk(symmetryConnectServerHandler.serverToSymmetryConnectJsonMessageConnectId, 
							{"symmetryConnectId":symmetryConnectId, "opt":opt}):
			data += d
		return data

	def dataChunk(self,symmetryConnectId, data):
		chunkLength = 1024 * 32
		while len(data) > 0:
			dataSend = data[:chunkLength]
			data = data[chunkLength:]
			dataSend = self.des.encrypt(dataSend)
			yield struct.pack("i", symmetryConnectId) + struct.pack("h", len(dataSend)) + dataSend + "\n"
	
	def onRecv(self, data):
		sockConnect.onRecv(self, data)
		self._symmetryConnectMessageBuffer += data
		self._connectIsLive = True
		_headSize = symmetryConnectServerHandler._headSize
		while True:
			bufferLen = len(self._symmetryConnectMessageBuffer)
			if bufferLen >= _headSize:
				symmetryConnectId, dataSize = struct.unpack("ih", self._symmetryConnectMessageBuffer[:_headSize])
				endIndex = dataSize + _headSize
				if bufferLen > endIndex:
					dataMessage = self._symmetryConnectMessageBuffer[_headSize:endIndex]
					self._symmetryConnectMessageBuffer = self._symmetryConnectMessageBuffer[endIndex + 1:]
					self._onRecvData(symmetryConnectId, dataMessage)
					continue
			break
	
	def _onRecvData(self, symmetryConnectId, data):
		if symmetryConnectId < 0:
			try:
				serverMessage = json.loads(data)
			except:
				return
			if symmetryConnectId == symmetryConnectServerHandler.serverToServerJsonMessageConnectId:
				self.onServerToServerMessage(serverMessage)
			elif symmetryConnectId == symmetryConnectServerHandler.serverToSymmetryConnectJsonMessageConnectId:
				connect = self.getSymmetryConnect(serverMessage["symmetryConnectId"])
				if connect:
					connect.onSymmetryConnectOpt(serverMessage["opt"])
		else:
			connect = self.getSymmetryConnect(symmetryConnectId)
			if connect:
				connect.onSymmetryConnectData(data)

	def getSymmetryConnect(self, symmetryConnectId):
		return self.symmetryConnectList[symmetryConnectId] if symmetryConnectId in self.symmetryConnectList else None

# -----------
	def sendOpt(self, symmetryConnectId, opt):
		self.send(self.optChunk(symmetryConnectId, opt))

	def sendData(self, symmetryConnectId, data):
		for d in self.dataChunk(symmetryConnectId, data):
			self.send(d)

	def addSymmetryConnect(self, connect, connectId):
		connect.symmetryConnectId = connectId
		connect.symmetryConnectManager = self
		self.symmetryConnectList[connectId] = connect
		
	def makeSymmetryConnectId(self):
		self.symmetryConnectIdLoop += 1
		return self.symmetryConnectIdLoop
