from .remoteServerHandler import realServerConnect


class fakeSymmetryConnectServerHandler:

	def __init__(self, server):
		self.server = server
		self.connectList = {}

	def addLocalRealConnect(self, localConnect):
		r = realServerConnect(self.server)
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

	def send(self, data):
		self.server.addCallback(self.doSend)

	def doSend(self):
		deleteList = []
		sended = False
		for l, r in self.connectList.items():
			if self.sendData(l, r):
				sended = True
			elif self.sendData(r, l):
				sended = True
			elif l.requestRemove():
				deleteList.append(l)
		for 	l in deleteList:
			r = self.connectList[l]
			r.close()
			del self.connectList[l]
		if sended:
			self.server.addCallback(self.doSend)

	def filenoStr(self):
		return "local"
