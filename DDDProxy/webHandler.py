#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dxw
'''
from gittornado import BaseHandler
import tornado
import DDDProxyConfig
from DDDProxy import domainConfig
from DDDProxy.hostParser import parserUrlAddrPort, getDomainName
import json
from DDDProxy.server import baseServer

class DDDProxyBaseHandler(BaseHandler):
	
	def getRequestHost(self):
		addrPort = parserUrlAddrPort(self.request.protocol + "://" + self.request.host);
		return addrPort[0]
	def finish(self, chunk=None):
		BaseHandler.finish(self, chunk=chunk)
		baseServer.log(2,self.request.remote_ip, (self.request.method,self.request.host,self.request.uri,self.request.headers["User-Agent"]),
					(self._status_code,self._headers))
	def get_template_path(self):
		return "./template/";

class pacHandler(DDDProxyBaseHandler):
	@tornado.web.asynchronous
	def get(self):
		self.set_header("Content-Type", "application/javascript")
		self.render("pac.js", proxy_ddr="%s:%d" % (self.getRequestHost(), DDDProxyConfig.localServerProxyListenPort),
				domainList=domainConfig.config.getDomainOpenedList())

class helpHandler(DDDProxyBaseHandler):
	@tornado.web.asynchronous
	def get(self):
		pacAddrOrigin = "%s://%s/pac"%(self.request.protocol,self.request.host)
		self.render("fq_temp.html", info="",remoteAddr=DDDProxyConfig.remoteServerHost, pacAddr=pacAddrOrigin,pacAddrOrigin=pacAddrOrigin)
class adminHandler(DDDProxyBaseHandler):
	@tornado.web.asynchronous
	def get(self):
		opt = self.get_argument('opt',"").encode('utf8')
		if opt == "":
			self.render("admin_temp.html")
		else:
			if opt == "puturl":
				addr,port = parserUrlAddrPort(self.get_argument("url").encode('utf8'))
				if addr:
					domain = getDomainName(addr)
					if domainConfig.config.addDomain(domain):
						domainConfig.config.save()
				self.redirect("/admin", False)
			else:
				domain = self.get_argument("domain",default="").encode('utf8')
				ok = False
				if opt == "delete":
					ok = domainConfig.config.removeDomain(domain)
				elif opt == "close":
					ok = domainConfig.config.closeDomain(domain)
				elif opt == "open":
					ok = domainConfig.config.openDomain(domain)
				if ok:
					domainConfig.config.save()
				self.redirect("/admin", False)
	
	@tornado.web.asynchronous
	def post(self):
		postJson = json.loads(self.request.body)
		data = None
		opt = postJson["opt"]
		if opt=="domainList":
			data=domainConfig.config.getDomainListWithAnalysis()
		elif opt == "analysisDataList":
			data=domainConfig.analysis.getAnalysisData(postJson["domain"],postJson["startTime"])
		elif opt == "domainDataList":
			data = domainConfig.analysis.getTodayDomainAnalysis()
		self.set_header("Content-Type", "application/json")
		self.write(json.dumps(data))
		self.finish()
