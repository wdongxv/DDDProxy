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
from DDDProxy.server import baseServer
from DDDProxy.localProxyServerHandler import proxyServerHandler
import sys
from DDDProxy import domainConfig
from gittornado import BaseHandler
import threading
import httplib
import traceback
import time
import autoProxy

settings = {
	"debug":False,
}
def printError():
	logging.error(sys.exc_info())
	logging.error(traceback.format_exc())
	pass
class statusPage(BaseHandler):
	@tornado.web.asynchronous
	def get(self):
		opt = self.get_argument("opt",default="")
		if opt:
			opt = opt.encode("utf8")
			
		if opt == "remoteProxy":
			status = "connected"
			try:
				test = proxyServerHandler(conn=None, addr=["",""], threadid=None)
				test.connRemoteProxyServer()
				test.close()
			except:
				printError()
				status = "can not connect"
			self.write({"status":status})
		elif opt == "pac_setting_test_local":
			self.write({"status":"fail"})
		elif opt == "testProxy":
			status = "ok"
			try:
				conn = httplib.HTTPConnection(host='127.0.0.1',port=DDDProxyConfig.localServerProxyListenPort,timeout=10)
				conn.connect()
				conn.request("GET", "http://www.baidu.com/",headers={})
				response = conn.getresponse()
				conn.close()
			except:
				status = "fail"
			self.write({"status":status})
		else:
			currentThread = threading.enumerate()
			threadList = []
			for t in currentThread:
				threadList.append({"name":t.name})
			data={"threading:":threadList}
			self.write(data)
		self.finish()
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
	remoteServerIp = None if len(sys.argv) < 2 else sys.argv[1];
	DDDProxyConfig.remoteServerAuth = None if len(sys.argv) < 3 else sys.argv[2];
	if not remoteServerIp or not DDDProxyConfig.remoteServerAuth:
		exit("please use \"python localServer.py [remoteServerHost] [passWord]\"")
	
	if remoteServerIp:
		if remoteServerIp.find(':') > 0:
			DDDProxyConfig.remoteServerHost,DDDProxyConfig.remoteServerListenPort = remoteServerIp.split(':')
		else:
			DDDProxyConfig.remoteServerHost = remoteServerIp
	try:
		localProxyServer = baseServer(DDDProxyConfig.localServerListenIp, DDDProxyConfig.localServerProxyListenPort, proxyServerHandler)
		localProxyServer.start(True)
	except:
		logging.error(sys.exc_info())
	
	domainConfig.domainAnalysis.startAnalysis()
	autoProxy.AutoFetchGFWList()
	baseServer.log(2,"pac server start on %s:%d!" % (DDDProxyConfig.localServerListenIp, DDDProxyConfig.localServerAdminListenPort));
	application.listen(DDDProxyConfig.localServerAdminListenPort, DDDProxyConfig.localServerListenIp)
	tornado.ioloop.IOLoop.instance().start()
