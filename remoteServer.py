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
if __name__ == "__main__":
	server = baseServer(handler=remoteServerHandler.remoteConnectServerHandler)
	remoteServerHandler.createSSLCert()
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
	s.bind(("", 8889))
	s.listen(1024)
	s = ssl.wrap_socket(s, certfile=remoteServerHandler.SSLCertPath,keyfile=remoteServerHandler.SSLKeyPath, server_side=True)
	
	server.addSockListen(s)
	server.start()