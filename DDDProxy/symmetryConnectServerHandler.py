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
from Crypto.Cipher import AES
import binascii
import hashlib


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
# 			if len(self._symmetryConnectSendPendingCache) > 100 and not self._pauseRecv:
# 				self._pauseRecv = True
# 				self.setIOEventFlags(0)
		if addData:
			self.requestSymmetryConnectManagerWrite()
		else:
			pass

	def requestSymmetryConnectManagerWrite(self):
		if self.symmetryConnectSendPending():
			if not self.symmetryConnectManager:
				pass
			else:
				self.symmetryConnectManager.send(b"")

#--------------- for symmetryConnectServerHandler
	def symmetryConnectSendPending(self):
		return len(self._symmetryConnectSendPendingCache)

	def getSymmetryConnectSendData(self):
		sendData = b""
		sendOpt = b""
		while len(self._symmetryConnectSendPendingCache) > 0 and len(sendData) < 1024 * 8:
			data = self._symmetryConnectSendPendingCache.pop(0)
			if type(data) == bytes:
				for part in self.symmetryConnectManager.dataChuck.dataChunk(self.symmetryConnectId, data):
					sendData += part
			elif type(data) == int:
				sendOpt = self.symmetryConnectManager.dataChuck.optChunk(self.symmetryConnectId, data)
				break
			else:
				raise BaseException("type error:" + str(type(data)))
		if self._pauseRecv and len(self._symmetryConnectSendPendingCache) < 100:
			flags = sockConnect.socketIOEventFlagsRead
			if self.getSendPending():
				flags |= sockConnect.socketIOEventFlagsWrite
			self.setIOEventFlags(flags)
			self._pauseRecv = False
		return sendData + sendOpt

	def requestRemove(self):
		return self._requestRemove


class encryptDataChuck():

	def __init__(self, auth, logPrefix="Recv"):
		self._symmetryConnectMessageBuffer = b""
		self._symmetryConnectMessageCryptBuffer = b""
		key32 = [ ' ' if i >= len(auth) else auth[i] for i in range(32) ]
		self.aes = AES.new(''.join(key32), AES.MODE_ECB)
		self.logPrefix = logPrefix
		self.dataLog = open("/tmp/dddproxy." + logPrefix + ".log", mode='a+')
		self.md5Match = True

	_structFormat = "iii"
	_headSize = struct.calcsize(_structFormat) + 4
	
	def optChunk(self, symmetryConnectId, opt):
		data = b""
		for d in self.dataChunk(symmetryConnectServerHandler.serverToSymmetryConnectJsonMessageConnectId,
							json.dumps({"symmetryConnectId":symmetryConnectId, "opt":opt}).encode()):
			data += d
		return data

	chunkId = 0
	chunkLength = 1024 * 32

	def dataChunk(self, symmetryConnectId, data):
		while len(data) > 0:
			dataSend = data[:encryptDataChuck.chunkLength]
			data = data[encryptDataChuck.chunkLength:]
			dataSendLength = len(dataSend)
			encryptDataChuck.chunkId += 1
			dataSend = struct.pack(encryptDataChuck._structFormat, encryptDataChuck.chunkId, symmetryConnectId, dataSendLength) + hashlib.md5(dataSend).digest()[:4] + dataSend
			encryptData = b""
			while len(dataSend) > 0:
				encryptData += self.encryptData(dataSend[:16])
				dataSend = dataSend[16:]
# 			log.log(1,"Crea","dataChunk:%d"%encryptDataChuck.chunkId, "symmetryConnectId:%d"%symmetryConnectId, "len(dataSend):%d"%dataSendLength, "encryptData:%d"%len(encryptData))
			yield encryptData

	def encryptData(self, chunk):
		while len(chunk) < 16:
			chunk += b'\x00'
		return self.aes.encrypt(chunk)

	def dataChunkParse(self, data):
		self._symmetryConnectMessageCryptBuffer += data
		while len(self._symmetryConnectMessageCryptBuffer) >= 16:
			self._symmetryConnectMessageBuffer += self.aes.decrypt(self._symmetryConnectMessageCryptBuffer[:16])
			self._symmetryConnectMessageCryptBuffer = self._symmetryConnectMessageCryptBuffer[16:]
		self.dataLog.write(binascii.hexlify(data+b"\n").decode())
		self.dataLog.flush()
		if not self.md5Match:
			self._symmetryConnectMessageBuffer = b""
			return 
		while True:
			bufferSize = len(self._symmetryConnectMessageBuffer)
			if bufferSize >= encryptDataChuck._headSize:
				headData = self._symmetryConnectMessageBuffer[:encryptDataChuck._headSize - 4]
				chunkId, symmetryConnectId, dataSizeInt = struct.unpack(encryptDataChuck._structFormat, headData)
				md5Bytes = self._symmetryConnectMessageBuffer[encryptDataChuck._headSize - 4:encryptDataChuck._headSize]
				if dataSizeInt <= 0 or dataSizeInt > encryptDataChuck.chunkLength:
					log.log(2, headData, self.encryptData(headData))
					raise BaseException("bad dataSizeInt")
				encryptChuckSize = dataSizeInt + encryptDataChuck._headSize
				encryptChuckSize += (16 - (encryptChuckSize % 16)) % 16
				if bufferSize >= encryptChuckSize:
					dataMessage = self._symmetryConnectMessageBuffer[encryptDataChuck._headSize:encryptDataChuck._headSize + dataSizeInt]
					self._symmetryConnectMessageBuffer = self._symmetryConnectMessageBuffer[encryptChuckSize:]
					self.md5Match = md5Bytes == hashlib.md5(dataMessage).digest()[:4]
					data = 	" ".join(str(i) for i in ["dataChunk:%d" % chunkId, symmetryConnectId, self.md5Match, len(dataMessage)])
					self.dataLog.write(data + "\n")
					self.dataLog.flush()
					if not self.md5Match:
						log.log(2, "if not self.md5Match:", "dataChunk:%d" % chunkId, symmetryConnectId, self.md5Match)
						self.dataLog.write("if not self.md5Match: \n")
						break
					yield symmetryConnectId, dataMessage
					continue
			break

		
class symmetryConnectServerHandler(sockConnect):

	serverToServerJsonMessageConnectId = -1
	serverToSymmetryConnectJsonMessageConnectId = -2
	
	def __init__(self, server, auth, *args, **kwargs):
		sockConnect.__init__(self, server, *args, **kwargs)
		self.symmetryConnectList = {}
		self.symmetryConnectIdLoop = 0
		self.slowConnectStatus = False
		self._connectIsLive = True
		self._forcePing = 0
		self.info["pingSpeed"] = 0
		self.initOk = False
		className = str(self.__class__.__name__)
		self.dataChuck = encryptDataChuck(auth, className + ".Recv")
		self.dataChuckTest = encryptDataChuck(auth, className + ".Send")

	def onConnected(self):
		sockConnect.onConnected(self)
		self.sendServerMessage({"opt":"init"})
		self.sendPingSpeedResponse()
		log.log(2, self, "onConnected")

	def onSend(self, data):
		for _ in self.dataChuckTest.dataChunkParse(data):
			_ = b"" 
		sockConnect.onSend(self, data)

	def getSendData(self, length):
		while sockConnect.getSendPending(self) <= socketBufferMaxLenght * 2:
			found = False
			deleteList = []
			for symmetryConnectId, v in self.symmetryConnectList.items():
				if v.symmetryConnectSendPending():
					data = v.getSymmetryConnectSendData()
					found = True
					try:
						self.send(data)
					except:
						raise Exception(data, "is generator??")
				elif v.requestRemove():
					deleteList.append(symmetryConnectId)
					if len(self.symmetryConnectList) == 0:
						self.server.addDelay(30, self.requestIdleClose)
			for 	symmetryConnectId in deleteList:
				del self.symmetryConnectList[symmetryConnectId]
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
		
	def sendServerMessage(self, data):
		for d in self.dataChuck.dataChunk(symmetryConnectServerHandler.serverToServerJsonMessageConnectId, json.dumps(data).encode()):
			self.send(d)

	def onServerToServerMessage(self, serverMessage):
		opt = serverMessage["opt"] if "opt" in  serverMessage else ""
		if opt == "pingSpeed":
			serverMessage["opt"] = "pingSpeedResponse"
			self.sendServerMessage(serverMessage)
		elif opt == "pingSpeedResponse":
			useTime = time.time() - serverMessage["time"]
			self.info["lastPingSendTime"] = serverMessage["time"]
			self.info["pingSpeed"] = useTime
# 			log.log(2, self, "recv pingSpeedResponse", useTime)
			self.server.cancelCallback(self.setStatusSlow)
			self.server.cancelCallback(self.requestSlowClose)
			self.server.addDelay(30, self.sendPingSpeedResponse)
		elif opt == "init":
			self.initOk = True

	def sendPingSpeedResponse(self):
		return
		if self._connectIsLive and self._forcePing < 10 and self.info["pingSpeed"] != 0:
			self.server.addDelay(5, self.sendPingSpeedResponse)
			self._forcePing += 1
		else:
			self._forcePing = 0
			self.sendServerMessage({
				"opt":"pingSpeed",
				"time":time.time()
			})
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
		
	def onRecv(self, data):
		sockConnect.onRecv(self, data)
		
		self._connectIsLive = True
		for symmetryConnectId, dataMessage in self.dataChuck.dataChunkParse(data):
			if not symmetryConnectId:
				self.close()
			else:
				self._onRecvData(symmetryConnectId, dataMessage)
	
	def _onRecvData(self, symmetryConnectId, data):
		if symmetryConnectId < 0:
			try:
				serverMessage = json.loads(data.decode())
			except:
				self.close()
				if self.initOk:
					log.log(2, self, "if self.initOk: raise", "symmetryConnectId", symmetryConnectId)
					raise BaseException("json.loads(data.decode()) error")
				else:
					log.log(2, self, "if not self.initOk, not raise", "symmetryConnectId", symmetryConnectId)
			if symmetryConnectId == symmetryConnectServerHandler.serverToServerJsonMessageConnectId:
				self.onServerToServerMessage(serverMessage)
			elif symmetryConnectId == symmetryConnectServerHandler.serverToSymmetryConnectJsonMessageConnectId:
				connect = symmetryConnectServerHandler.getSymmetryConnect(self, serverMessage["symmetryConnectId"])
				if connect:
					connect.onSymmetryConnectOpt(serverMessage["opt"])
			else:
				log.log(3, self, "symmetryConnectId not match")
				self.close()
		elif not self.initOk:
			log.log(3, self, "elif not self.initOk:")
			self.close()
		else:
			connect = self.getSymmetryConnect(symmetryConnectId)
			if connect:
				connect.onSymmetryConnectData(data)

	def getSymmetryConnect(self, symmetryConnectId):
		return self.symmetryConnectList[symmetryConnectId] if symmetryConnectId in self.symmetryConnectList else None

# -----------

	def addSymmetryConnect(self, connect, connectId):
		connect.symmetryConnectId = connectId
		connect.symmetryConnectManager = self
		self.symmetryConnectList[connectId] = connect
		
	def makeSymmetryConnectId(self):
		self.symmetryConnectIdLoop += 1
		return self.symmetryConnectIdLoop


if __name__ == "__main__":
	log.debuglevel = 1
	d = encryptDataChuck("ddd")
	testByte = b""
	for i in range(3):
		testByte += bytes([b"abcdefghijklmnopqrstuvwxyz"[i % 26]])
		for data in d.dataChunk(i, testByte):
			for pid, pdata in d.dataChunkParse(data):
				print(i, pid, pdata == testByte, pdata, testByte)
