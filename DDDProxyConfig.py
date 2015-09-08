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
from twisted.python.threadpool import ThreadPool

localServerProxyListenPort = 8080
localServerAdminListenPort = 8081
localServerListenIp = "0.0.0.0"


remoteServerListenPort = 8083
remoteServerListenIp = "0.0.0.0"
remoteServerAuth = None


#在此列表的host走代理时会被block，远程和本地服务都会做处理
blockHost = ["10.0.1","192.168.1","127.0.0.1","localhost"]

debuglevel = 2
timeout = 600
cacheSize = 1024 * 2


baseDir = dirname(__file__)

mainThreadPool = ThreadPool(maxthreads=10000)
mainThreadPool.start()
def SSLLocalCertPath(remoteServerHost,remoteServerPort):
	return baseDir+"/tmp/cert.%s-%d.pem"%(remoteServerHost,remoteServerPort)

SSLCertPath =  baseDir+"/tmp/cert.remote.pem"
SSLKeyPath =  baseDir+"/tmp/key.remote.pem"

pacDomainConfig =  baseDir+"/tmp/DDDProxy.domain.json"
domainAnalysisConfig =  baseDir+"/tmp/DDDProxy.domainAnalysis.json"
settingConfigPath =  baseDir+"/tmp/DDDProxy.setting.json"

createCertLock = 	threading.RLock()
def fetchRemoteCert(remoteServerHost,remoteServerPort):
	createCertLock.acquire()
	try:
		if not os.path.exists(SSLLocalCertPath(remoteServerHost,remoteServerPort)):
			cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerPort))
			open(SSLLocalCertPath(remoteServerHost,remoteServerPort), "wt").write(cert)
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

