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

blockHost = []

debuglevel = 1
timeout = 600
cacheSize = 1024 * 2


baseDir = dirname(__file__)

SSLLocalCertPath =  baseDir+"/tmp/cert.local.pem"
SSLCertPath =  baseDir+"/tmp/cert.remote.pem"
SSLKeyPath =  baseDir+"/tmp/key.remote.pem"

pacDomainConfig =  baseDir+"/tmp/DDDProxy.domain.json"

domainAnalysisConfig =  baseDir+"/tmp/DDDProxy.domainAnalysis.json"

createCertLock = 	threading.RLock()
def fetchRemoteCert():
	createCertLock.acquire()
	if not os.path.exists(SSLLocalCertPath):
		cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerListenPort))
		open(SSLLocalCertPath, "wt").write(cert)
	createCertLock.release()

def createSSLCert():
	createCertLock.acquire()
	if not os.path.exists(SSLCertPath) or not os.path.exists(SSLCertPath):
		shell = "openssl req -new -newkey rsa:1024 -days 3650 -nodes -x509 -subj \"/C=US/ST=Denial/L=Springfield/O=Dis/CN=dddproxy\" -keyout %s  -out %s"%(
																							SSLKeyPath,SSLCertPath)
		os.system(shell)

	createCertLock.release()

