#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年1月11日

@author: dx.wang
'''
import os
import ssl
import threading
import random
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
	from OpenSSL import crypto
	createCertLock.acquire()
	if not os.path.exists(SSLCertPath) or not os.path.exists(SSLCertPath):
		k = crypto.PKey()
		k.generate_key(crypto.TYPE_RSA, 1024)
		cert = crypto.X509()
		cert.get_subject().C = "CN"
		cert.get_subject().ST = "%f"%(random.random()*10)
		cert.get_subject().L = "%f"%(random.random()*10)
		cert.get_subject().O = "%f"%(random.random()*10)
		cert.get_subject().OU = "%f"%(random.random()*10)
		cert.get_subject().CN = "%f"%(random.random()*10)
		
		cert.set_serial_number(1000)
		cert.gmtime_adj_notBefore(0)
		cert.gmtime_adj_notAfter(315360000)
		cert.set_issuer(cert.get_subject())
		cert.set_pubkey(k)
		cert.sign(k, 'sha1')
		
		certPem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
		keyPem = crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
		
		open(SSLCertPath, "wt").write(certPem)
		open(SSLKeyPath, "wt").write(keyPem)

	createCertLock.release()

