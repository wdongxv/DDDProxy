# import re
# class socetMessageParser():
# 	def __init__(self):
# 		self.message = ""
# 		self.lastMessage = ""
# 	def clear(self):
# 		self.lastMessage = self.message
# 		self.message = ""
# 		
# 	def putMessage(self, data):
# 		self.message += data
# 	
# 	def messageStatus(self):
# 		method, path, protocol = self.httpMessage()
# 		if protocol:
# 			headers = self.httpHeaders()
# 			if not headers is None:
# 				if method == "POST":
# 					if "content-length" in headers and (int(headers["content-length"]) <= len(self.httpBodyStr())):
# 						return 1
# 				else:
# 					return 1
# 		return 0
# 
# 	def messageData(self):
# 		return self.message
# 		
# 	def httpMessage(self):
# 		if self.message.find("\r\n") > 0:
# 			firstLine = self.message.split('\r\n', 1)[0]
# 			try:
# 				method, path, protocol = firstLine.split()
# 				if re.match("HTTP/\d.\d", protocol):
# 					return method, path, protocol
# 			except:
# 				pass
# 		return "", "", ""
# 	def httpHeadersStr(self):
# 		method, path, protocol = self.httpMessage()
# 		if not protocol:
# 			return ""
# 		return self.message.split("\r\n\r\n", 1)[0]
# 	def httpBodyStr(self):
# 		method, path, protocol = self.httpMessage()
# 		if not protocol:
# 			return ""
# 		return self.message.split("\r\n\r\n", 1)[1]
# 	def httpHeaders(self):
# 		header = self.httpHeadersStr()
# 		if not header:
# 			return None
# 		headers = {}
# 		for item in header.lower().split("\r\n")[1:]:
# 			k, v = item.split(": ")
# 			headers[k] = v
# 		return headers




import re
class httpMessageParser():
	def __init__(self):
		self.clear()
		
	def clear(self):
		self.messageCache = ""
		self.protocol = None#(method, path, protocol)
		self.headers = []
		self.status	= "readding"
	def method(self):
		return self.protocol[0]
	def path(self):
		return self.protocol[1]
	def getHeader(self,key):
		k = key.lower()
		for h in self.headers:
			if h[0] == k:
				return h[1]
		return None
	def connection(self):
		connection = self.getHeader("connection")
		return "keep-alive" if connection and connection=="keep-alive" else "close"
	def appendData(self, data):
		if self.status != "readding":
			return
		self.messageCache += data
		while True:
			index = self.messageCache.find("\r\n")
			if index <0 :
				return False
			
			line = self.messageCache[:index]
			self.messageCache = self.messageCache[index+2:]
			if self.protocol:
				if index == 0:
					self.messageCache = self.messageCache[2:]
					self.status = "end"
					return True
				header = line.split(": ")
				if(len(header)==2):
					self.headers.append((header[0].lower(),header[1]))
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
	def messageStatus(self):
		method, path, protocol = self.httpMessage()
		if protocol:
			headers = self.httpHeaders()
			if not headers is None:
				if method == "POST":
					if "content-length" in headers and (int(headers["content-length"]) <= len(self.httpBodyStr())):
						return 1
				else:
					return 1

		return 0


