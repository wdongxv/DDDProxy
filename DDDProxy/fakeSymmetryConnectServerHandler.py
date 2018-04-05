from .remoteServerHandler import realServerConnect
from DDDProxy import domainConfig
from .hostParser import getDomainName
class fakeRealServerConnect(realServerConnect):
	def connect(self, address, cb=None):
		def connectOk(error,connect):
			if error:
				if error == "timed out" or error == "[Errno 54] Connection reset by peer" or error == "[Errno 61] Connection refused":
					domainConfig.config.openDomain(connect.address[0])
			if cb:
				cb(error,connect) 
		return realServerConnect.connect(self, address, cb=connectOk)

class fakeSymmetryConnectServerHandler:

	def __init__(self, server):
		self.server = server
		self.connectList = {}

	def addLocalRealConnect(self, localConnect):
		r = fakeRealServerConnect(self.server)
		r.symmetryConnectManager = self
		self.connectList[localConnect] = r
	
	def sendData(self, c1, c2):
		if  c1.symmetryConnectSendPending():
			data = c1._symmetryConnectSendPendingCache.pop(0)
			if type(data) == bytes:
				c2.onSymmetryConnectData(data)
			elif type(data) == int:
				c2.onSymmetryConnectOpt(data)
			return True
		return False

	def send(self, _):
		self.server.addCallback(self.doSend)

	def doSend(self):
		deleteList = []
		sended = False
		for l, r in self.connectList.items():
			if self.sendData(l, r):
				sended = True
			elif self.sendData(r, l):
				sended = True
			elif l.requestRemove() or r.requestRemove():
				deleteList.append(l)
		for 	l in deleteList:
			r = self.connectList[l]
			r.close()
			l.close()
			del self.connectList[l]
		if sended:
			self.server.addCallback(self.doSend)

	def filenoStr(self):
		return "local"
