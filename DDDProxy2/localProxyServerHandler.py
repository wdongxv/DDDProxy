#!/usr/bin/env python
# -*- coding: utf-8 -*-


from baseServer import sockConnect
from socetMessageParser import httpMessageParser
import StringIO
from tornado.httpclient import HTTPResponse
import datetime
from httplib import HTTPMessage
import httplib
from datetime import datetime
from DDDProxy2.baseServer import baseServer




class localProxyServerConnectHandler(sockConnect):
	def __init__(self, *args, **kwargs):
		sockConnect.__init__(self, *args, **kwargs)
		self.messageParse = httpMessageParser()
		self.mode = "proxy"
	def onRecv(self, data):
		if self.messageParse.appendData(data):
			method = self.messageParse.method()
			path = self.messageParse.path()
			if method == "GET" and not path.startswith("http://"):
				self.onGet(path,self.messageParse.headers)
				self.mode = "http"
				return

	def onSend(self, data):
		sockConnect.onSend(self, data)
		if self.messageParse.connection() == "close":
			self.close()
		self.messageParse.clear()
		
	def reseponse(self,data,type="text/html",code=200):
		def httpdate():
			dt = datetime.now();
			weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
			month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
					"Oct", "Nov", "Dec"][dt.month - 1]
			return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
		        dt.year, dt.hour, dt.minute, dt.second)
		httpMessage = ""
		httpMessage += "HTTP/1.1 "+str(code)+" "+(httplib.responses[code])+"\r\n"
		httpMessage += "Server: DDDProxy/2.0\r\n"
		httpMessage += "Date: "+httpdate()+"\r\n"
		httpMessage += "Content-Length: "+str(len(data))+"\r\n"
		httpMessage += "Content-Type: "+type+"\r\n"
		httpMessage += "Connection: "+self.messageParse.connection()+"\r\n"
		
		connection = self.messageParse.getHeader("connection")
		
		httpMessage += "\r\n"
		httpMessage += data
		self.send(httpMessage)
		
	def onGet(self,path,header):
		if path == "/":
			self.reseponse(str(header))
		else:
			self.reseponse("path not found",404)
		
if __name__ == "__main__":
	server = baseServer(handler=localProxyServerConnectHandler)
	server.addListen(port=8888)
	server.start()
