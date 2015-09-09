#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
from DDDProxy.baseServer import baseServer
from DDDProxy.localProxyServerHandler import localProxyServerConnectHandler
from DDDProxy.remoteConnectManger import remoteConnectManger


if __name__ == "__main__":
	server = baseServer(handler=localProxyServerConnectHandler)
	remoteConnectManger.install(server)
	server.addListen(port=8888)
	server.start()
	
	
	