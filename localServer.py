#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
from optparse import OptionParser

from DDDProxy import baseServer, log, gfwList, remoteServerHandler
from DDDProxy.domainAnalysis import domainAnalysis
from DDDProxy.localProxyServerHandler import localConnectHandler
from DDDProxy import localToRemoteConnectManger
import multiprocessing
import time
import sys

if __name__ == "__main__":
	
	parser = OptionParser()
	parser.add_option("-p", "--port", help="proxy server bind port" , default="-1")
	parser.add_option("-l", "--loglevel", help="log level" , default=2)
	parser.add_option("-c", "--RemoteConnectLimit", help="one remote address connect limit" , default=5)
	parser.add_option("-u", "--update", help="auto update on start" , default=True)
	parser.add_option("-f", "--logFile", help="log file path" , default="/tmp/dddproxy.local.log")
	
	startUpArgs = parser.parse_args()[0]
	
	log.install(int(startUpArgs.loglevel), startUpArgs.logFile)
	server = baseServer.baseServer()

	port = int("8080" if startUpArgs.port == "-1" else startUpArgs.port)
	domainAnalysis.startAnalysis(server)
	
	localToRemoteConnectManger.localToRemoteConnectManger.install(server, max(1, int(startUpArgs.RemoteConnectLimit)))
	gfwList.autoGFWList(server, port)
	
	
	def startLocalProxy():
		s = baseServer.baseServer()
		s.addListen(handler=remoteServerHandler.remoteServerHandler,port=57238,host="127.0.0.1")
		def checkMainLive():
			if mainLastRuntime.value + 10 < time.time():
				sys.exit()
			s.addDelay(5, checkMainLive)
		checkMainLive();
		s.start()
	mainLastRuntime = multiprocessing.Value("d")
	multiprocessing.Process(target=startLocalProxy).start()
	
	def mainLive():
		mainLastRuntime.value = time.time()
		server.addDelay(5, mainLive)
	mainLive();
	server.addListen(handler=localConnectHandler, port=port)
	server.start()
	