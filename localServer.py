#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
from optparse import OptionParser

from DDDProxy import baseServer, log, gfwList
from DDDProxy.domainAnalysis import domainAnalysis
from DDDProxy.localProxyServerHandler import localConnectHandler
from DDDProxy import localToRemoteConnectManger
import random

if __name__ == "__main__":
	
	parser = OptionParser()
	parser.add_option("-p", "--port", help="proxy server bind port" , default="-1")
	parser.add_option("-l", "--loglevel", help="log level" , default=2)
	parser.add_option("-c", "--RemoteConnectLimit", help="one remote address connect limit" , default=5)
	parser.add_option("-u", "--update", help="auto update on start" , default=True)
	
	startUpArgs = parser.parse_args()[0]
	
	log.debuglevel = int(startUpArgs.loglevel)
	
	server = baseServer.baseServer()

	port = int("8080" if startUpArgs.port == "-1" else startUpArgs.port)
	domainAnalysis.startAnalysis(server)
	
	localToRemoteConnectManger.localToRemoteConnectManger.install(server, max(1, int(startUpArgs.RemoteConnectLimit)))
	gfwList.autoGFWList(server, port)
	
	server.addListen(handler=localConnectHandler, port=port)
	server.start()
	
