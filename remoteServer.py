#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
from DDDProxy.baseServer import baseServer
from DDDProxy import remoteServerHandler
import socket
import ssl
from optparse import OptionParser
if __name__ == "__main__":
	
	parser = OptionParser(usage="%prog -a [password]")
	parser.add_option("-a", "--auth",help="server password *")
	parser.add_option("-p", "--port",help="bind port" , default=8082)
	parser.add_option("-l", "--loglevel",help="log level" , default=2)
	startUpArgs = parser.parse_args()[0]
	remoteServerHandler.remoteAuth =  startUpArgs.auth
	if not remoteServerHandler.remoteAuth:
		print parser.get_usage()
		exit()
		
	baseServer.debuglevel = int(startUpArgs.loglevel)
		
	remoteServerHandler.createSSLCert()
	
	server = baseServer(handler=remoteServerHandler.remoteConnectServerHandler)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
	s.bind(("", int(startUpArgs.port)))
	s.listen(1024)
	s = ssl.wrap_socket(s, certfile=remoteServerHandler.SSLCertPath,keyfile=remoteServerHandler.SSLKeyPath, server_side=True)
	
	server.addSockListen(s)
	server.start()