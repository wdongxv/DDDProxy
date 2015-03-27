#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
from DDDProxy.server import baseServer
import DDDProxyConfig
from DDDProxy.remoteServerHandler import remoteServerHandler
import sys

if __name__ == '__main__':
	DDDProxyConfig.remoteServerAuth = None if len(sys.argv) < 2 else sys.argv[1];
	if not DDDProxyConfig.remoteServerAuth:
		exit("please set remote server password, use \"python remoteServer.py [passWord]\"")
	
	remoteServerIp = None if len(sys.argv) < 3 else sys.argv[2];
	if remoteServerIp:
		if remoteServerIp.find(':') > 0:
			DDDProxyConfig.remoteServerListenIp,DDDProxyConfig.remoteServerListenPort = remoteServerIp.split(':')
		else:
			DDDProxyConfig.remoteServerListenPort = remoteServerIp
	
	server = baseServer(DDDProxyConfig.remoteServerListenIp, DDDProxyConfig.remoteServerListenPort, remoteServerHandler)
	server.start()
