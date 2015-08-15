#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
import tornado
import logging
import DDDProxyConfig
from DDDProxy.webHandler import pacHandler, helpHandler, adminHandler
from DDDProxy.server import baseServer, DDDProxySocketMessage
from DDDProxy.localProxyServerHandler import proxyServerHandler
import sys
from DDDProxy import domainConfig
from gittornado import BaseHandler
import threading
import httplib
import traceback
import time
import autoProxy
import thread
from DDDProxyConfig import mainThreadPool
import socket

settings = {
# 	"debug":True,
	'gzip': True,
# 	'autoreload':True
}
def printError():
	logging.error(sys.exc_info())
	logging.error(traceback.format_exc())
	pass
localProxyServer = None
class statusPage(BaseHandler):
	def __init__(self, application, request, **kwargs):
		BaseHandler.__init__(self, application, request, **kwargs)
		self.gethostbyaddrCache = {}
	def gethostbyaddr(self, ip):
		if ip in self.gethostbyaddrCache:
			h = self.gethostbyaddrCache[ip]
			if(h["time"] < time.time() + 3600 * 2):
				return h["host"]
		host = ip
		try:
			host = socket.gethostbyaddr(ip)[0]
		except:
			pass
		self.gethostbyaddrCache[ip] = {"host":host, "time":time.time()}
		return host
	def getInThread(self):
		opt = self.get_argument("opt", default="status")
		if opt:
			opt = opt.encode("utf8")
		
# 		threading.currentThread().name = "statusPage-%s"%(opt)
		if opt == "remoteProxy":
			status = "connected"
			try:
				port = self.get_argument("port", default=0)
				port = port if port else 8083
				test = proxyServerHandler(conn=None, addr=["", ""], threadid=None)
				test.connRemoteProxyServer(host=self.get_argument("host", default=""),
										port=int(port),
										auth=self.get_argument("auth", default=""))
				DDDProxySocketMessage.sendOne(test.remoteSocket, "[%s,%s]" % ("0.0.0.0", "test"))
				DDDProxySocketMessage.sendOne(test.remoteSocket,
															"CONNECT www.google.com:443 HTTP/1.1\r\n\r\n");
				status = "connected,auth no pass"
				for d in  DDDProxySocketMessage.recv(test.remoteSocket):
					if d == "HTTP/1.1 200 OK\r\n\r\n":
						status = "connected"
				test.close()
			except:
				printError()
				status = "can not connect"
			self.write({"status":status})
		elif opt == "pac_setting_test_local":
			self.write({"status":"fail"})
		else:
			working = []
			working.extend(t.name for t in mainThreadPool.working)
			idle = []
			idle.extend(t.name for t in mainThreadPool.waiters)
			
			connectList = {}
			for handler in localProxyServer.theadList:
				try:
					addrList = None
					addr = self.gethostbyaddr(handler.addr)
					if addr in connectList:
						addrList = connectList[addr]
					else:
						connectList[addr] = addrList = []
					addrList.append([handler.httpMessage[1] if (type(handler.httpMessage) == tuple and len(handler.httpMessage) > 2) else handler.httpMessage,
									handler.remoteServer,
									handler.dataCountSend,
									handler.dataCountRecv])
				except:
					printError()
			data = {
				"count":{
						"worker":len(mainThreadPool.working),
						"idle":len(mainThreadPool.waiters)
						},
				"thread":{
# 						"worker":working,
# 						"idle":idle
						"connect":connectList
						}
				}
			self.write(data)
		self.finish()
	@tornado.web.asynchronous
	def get(self):
		mainThreadPool.callInThread(self.getInThread)
class testPac(BaseHandler):
	@tornado.web.asynchronous
	def get(self):
		self.write({"status":"fail"})
		self.finish()

application = tornado.web.Application([
	(r"/pac", pacHandler),
	(r"/", helpHandler),
	(r"/admin/get_real_ip_p.php", testPac),
	(r"/admin", adminHandler),
	(r"/status", statusPage),
	(r"/static/(.+)", tornado.web.StaticFileHandler, {"path": "./static"}),
], **settings)

if __name__ == '__main__':
	try:
		localProxyServer = baseServer(DDDProxyConfig.localServerListenIp, DDDProxyConfig.localServerProxyListenPort, proxyServerHandler)
		localProxyServer.start(True)
	except:
		logging.error(sys.exc_info())
	
	domainConfig.domainAnalysis.startAnalysis()
# 	autoProxy.AutoFetchGFWList()
	baseServer.log(2, "pac server start on %s:%d!" % (DDDProxyConfig.localServerListenIp, DDDProxyConfig.localServerAdminListenPort));
	application.listen(DDDProxyConfig.localServerAdminListenPort, DDDProxyConfig.localServerListenIp)
	tornado.ioloop.IOLoop.instance().start()
