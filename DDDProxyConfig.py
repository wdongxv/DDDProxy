#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
import os
import ssl
import threading
from os.path import dirname

localServerProxyListenPort = 8080
localServerAdminListenPort = 8081
localServerListenIp = "0.0.0.0"


remoteServerHost = None


remoteServerListenPort = 8083
remoteServerListenIp = "0.0.0.0"
remoteServerAuth = None


#在此列表的host走代理时会被block，远程和本地服务都会做处理
blockHost = ["10.0.1","192.168.1","127.0.0.1","localhost"]

debuglevel = 2
timeout = 600
cacheSize = 1024 * 2


baseDir = dirname(__file__)

def SSLLocalCertPath():
	return baseDir+"/tmp/cert."+remoteServerHost+".pem"
					
SSLCertPath =  baseDir+"/tmp/cert.remote.pem"
SSLKeyPath =  baseDir+"/tmp/key.remote.pem"

pacDomainConfig =  baseDir+"/tmp/DDDProxy.domain.json"

domainAnalysisConfig =  baseDir+"/tmp/DDDProxy.domainAnalysis.json"

createCertLock = 	threading.RLock()
def fetchRemoteCert():
	createCertLock.acquire()
	try:
		if not os.path.exists(SSLLocalCertPath()):
			cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerListenPort))
			open(SSLLocalCertPath(), "wt").write(cert)
	except:
		pass
	createCertLock.release()

def createSSLCert():
	createCertLock.acquire()
	if not os.path.exists(SSLCertPath) or not os.path.exists(SSLCertPath):
		shell = "openssl req -new -newkey rsa:1024 -days 3650 -nodes -x509 -subj \"/C=US/ST=Denial/L=Springfield/O=Dis/CN=dddproxy\" -keyout %s  -out %s"%(
																							SSLKeyPath,SSLCertPath)
		os.system(shell)

	createCertLock.release()

