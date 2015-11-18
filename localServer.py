#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
from optparse import OptionParser
from DDDProxy import baseServer
from DDDProxy.domainAnalysis import domainAnalysis
from DDDProxy.localProxyServerHandler import localConnectHandler
from DDDProxy import localToRemoteConnectManger


if __name__ == "__main__":
	
	
	parser = OptionParser()
	parser.add_option("-p", "--port",help="proxy server bind port" , default=8080)
	parser.add_option("-l", "--loglevel",help="log level" , default=2)
	parser.add_option("-c", "--RemoteConnectLimit",help="one remote address connect limit" , default=2)
	
	startUpArgs = parser.parse_args()[0]
	
	
	baseServer.debuglevel = int(startUpArgs.loglevel)
	
	localToRemoteConnectManger.maxConnectByOnServer = max(1,int(startUpArgs.RemoteConnectLimit))
	
	server = baseServer.baseServer(handler=localConnectHandler)

	domainAnalysis.startAnalysis(server)
	localToRemoteConnectManger.localToRemoteConnectManger.install(server)
	
	server.addListen(port=int(startUpArgs.port))
	
	print "start server on: 0.0.0.0:"+str(startUpArgs.port)
	
	server.start()
	
	