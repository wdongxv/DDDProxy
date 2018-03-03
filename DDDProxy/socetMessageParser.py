
import re
import json
from DDDProxy import log
class httpMessageParser():
	def __init__(self):
		self.clear()
		
	def clear(self):
		self.messageCache = b""
		self.protocol = None  # (method, path, protocol)
		self.headers = []
		self.status	 = "readding"
		self.readingBodyLength = 0
	def method(self):
		return self.protocol[0]
	def path(self):
		return self.protocol[1]
	def httpVersion(self):
		return self.protocol[2]
	
	def HeaderString(self):
		message = ""
		for line in self.headers:
			message += "%s: %s\r\n" % (line[0], line[1])
		return message
	def getHeader(self, key):
		k = key.lower()
		for h in self.headers:
			if h[0].lower() == k:
				return int(h[1]) if key in ["content-length"] else h[1]
		return None
	def getBody(self):
		return self.messageCache
	def connection(self):
		connection = self.getHeader("connection")
		return "keep-alive" if (connection and connection.lower() == "keep-alive") else "close"
	def headerOk(self):
		return self.status == "end" or self.status == "bodyReadding" 
	def headerError(self):
		return self.status == "error" 
	def readingBody(self):
		m = self.messageCache
		self.readingBodyLength += len(m)
		self.messageCache = b""
		return m
	def appendData(self, data):
		if self.status == "bodyReadding":
			self.messageCache += data
			length = self.getHeader("content-length")
			if  length <= len(self.messageCache) + self.readingBodyLength:
				self.status = "end"
				return True
			return False
		
		if self.status != "readding":
			return
		self.messageCache += data
		while True:
			index = self.messageCache.find(b"\r\n")
			if index < 0 :
				return False
			
			line = self.messageCache[:index].decode()
			self.messageCache = self.messageCache[index + 2:]
			if self.protocol:
				if index == 0:
					if self.method() == "POST":
						self.status = "bodyReadding"
						return self.appendData(b"")
					self.status = "end"
					return True
				header = line.split(": ", 1)
				if(len(header) == 2):
					self.headers.append((header[0], header[1]))
				else:
					self.clear()
					self.status = "error"
			else:
				try:
					method, path, protocol = line.split()
					if re.match("HTTP/\d.\d", protocol):
						self.protocol = (method, path, protocol)
				except:
					self.status = "error"
		return False


