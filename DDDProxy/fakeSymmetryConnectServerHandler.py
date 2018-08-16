from .remoteServerHandler import realServerConnect
from DDDProxy import domainConfig, hostParser
from .hostParser import getDomainName
import re
class fakeRealServerConnect(realServerConnect):
	def connect(self, address, cb=None):
		def connectOk(error,connect):
			if error:
				if error == "timed out" or error == "[Errno 54] Connection reset by peer" or error == "[Errno 61] Connection refused":
					domain = connect.address[0]
					shortDomain = hostParser.getDomainName(domain);
					if shortDomain:
						domain = shortDomain
					if not domainConfig.config.domainIsExist(domain) and not domain in ["127.0.0.1", "localhost"] and not re.match("192\.168.+", domain) and not re.match("10\.0.+", domain):
						domainConfig.config.openDomain(domain)
			if cb:
				cb(error,connect) 
		return realServerConnect.connect(self, address, cb=connectOk)

class fakeSymmetryConnectServerHandler:

	def __init__(self, server):
		self.server = server
		self.connectList = {}
		self.doSendCalling = False
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
		if not self.doSendCalling:
			self.server.addCallback(self.doSend)
			self.doSendCalling = True
	def doSend(self):
		deleteList = []
		for l, r in self.connectList.items():
			self.sendData(l, r)
			self.sendData(r, l)
			if l.requestRemove or r.requestRemove:
				deleteList.append(l)
		for l in deleteList:
			r = self.connectList[l]
			r.close()
			l.close()
			del self.connectList[l]
		self.doSendCalling = False
	def filenoStr(self):
		return "local"
