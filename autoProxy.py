'''
Created on 2015-4-15

@author: dxw
'''
import DDDProxyConfig
import urllib2
import base64
import re
import urlparse
import thread
from DDDProxy import domainConfig
import time
import logging
from DDDProxy.server import baseServer

def getGFWHost():
	proxy = urllib2.ProxyHandler({"http":"127.0.0.1:%d" % (DDDProxyConfig.localServerProxyListenPort),
					"https":"127.0.0.1:%d" % (DDDProxyConfig.localServerProxyListenPort)})
	opener = urllib2.build_opener(proxy)
	urllib2.install_opener(opener)
	response = urllib2.urlopen('https://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt',timeout=30)
	gfwlist = base64.decodestring(response.read())
	line = ""
	hostList = []
	hostMatch = re.compile("^[\w\.-]+(\.)([a-zA-Z]{2,5})$");
	for line in gfwlist.split("\n"):
		if line.startswith("."):
			line = line[1:]
		elif line.startswith("||"):
			line = line[2:]
		elif line.startswith("|"):
			try:
				uri = urlparse.urlparse(line[1:])
				line = uri.netloc
			except:
				pass
		elif line.find("/") > 0:
			line = line.split("/")[0]
		if hostMatch.match(line) and not line in hostList:
			hostList.append(line)
	urllib2.install_opener(None)
	return hostList
def AutoGFWListThread():
	retryTime = 1
	while True:
		hostList = []
		try:
			baseServer.log(2,"fetch gfw list ....")
			hostList = getGFWHost()
		except:
			baseServer.log(3,"fetch gfw list error,retry in next %ds"%(retryTime))
			time.sleep(retryTime)
			retryTime *= 2
			continue
		retryTime = 1
		baseServer.log(2,"fetch gfw list %d hosts"%(len(hostList)))
		for host in hostList:
			domainConfig.config.addDomain(host,formGwflist=True)
		domainConfig.config.save()
		time.sleep(3600*24)
def AutoFetchGFWList():
	thread.start_new_thread(AutoGFWListThread, tuple())