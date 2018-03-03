#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
from DDDProxy.baseServer import baseServer
from DDDProxy import remoteServerHandler, log
import socket
from optparse import OptionParser
if __name__ == "__main__":
	
	parser = OptionParser(usage="%prog -a [password]")
	parser.add_option("-a", "--auth",help="server password *")
	parser.add_option("-p", "--port",help="bind port" , default="-1")
	parser.add_option("-l", "--loglevel",help="log level" , default=2)
	startUpArgs = parser.parse_args()[0]
	remoteServerHandler.remoteAuth =  startUpArgs.auth
	if not remoteServerHandler.remoteAuth:
		print parser.get_usage()
		exit()
		
	log.debuglevel = int(startUpArgs.loglevel)
	
	
	server = baseServer()
	server.addListen(handler=remoteServerHandler.remoteServerHandler,port=int("8083" if startUpArgs.port == "-1" else startUpArgs.port))
	server.start()
	