#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
from DDDProxy.localProxyServerHandler import localProxyServerConnectHandler
from optparse import OptionParser
from DDDProxy import baseServer, remoteConnectManger
from DDDProxy.domainAnalysis import domainAnalysis


if __name__ == "__main__":
	
	
	parser = OptionParser()
	parser.add_option("-p", "--port",help="proxy server bind port" , default=8080)
	parser.add_option("-l", "--loglevel",help="log level" , default=2)
	parser.add_option("-c", "--RemoteConnectLimit",help="one remote address connect limit" , default=2)
	
	startUpArgs = parser.parse_args()[0]
	
	
	baseServer.debuglevel = int(startUpArgs.loglevel)
	
	remoteConnectManger.maxConnectByOnServer = max(1,int(startUpArgs.RemoteConnectLimit))
	
	server = baseServer.baseServer(handler=localProxyServerConnectHandler)

	domainAnalysis.startAnalysis(server)
	remoteConnectManger.remoteConnectManger.install(server)
	
	server.addListen(port=int(startUpArgs.port))
	
	print "start server on: 0.0.0.0:"+str(startUpArgs.port)
	
	server.start()
	
	