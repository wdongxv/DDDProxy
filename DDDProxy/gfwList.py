'''
Created on 2015-4-15

@author: dxw
'''
import base64
import re
from DDDProxy import domainConfig
import urllib
from . import log
from DDDProxy.baseServer import sockConnect

gfwListFetchUrl = [
		# [url,retryTimes]
		["https://raw.githubusercontent.com/calfzhou/autoproxy-gfwlist/master/gfwlist.txt", 0]
		]


def _getGFWHost(server, setThreadName):
	"""
	@param server: _baseServer
	"""
	
	setThreadName("_get_GFW_Host_list")
	fecthUrl = None
	for i in gfwListFetchUrl:
		if fecthUrl is None or i[1] < fecthUrl[1] :
			fecthUrl = i
	try:
		response = urllib.request.urlopen(fecthUrl[0], timeout=30)
		gfwlist = base64.decodestring(response.read()).decode()
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
					uri = urllib.parse.urlparse(line[1:])
					line = uri.netloc
				except:
					pass
			elif line.find("/") > 0:
				line = line.split("/")[0]
			if hostMatch.match(line) and not line in hostList:
				hostList.append(line)
	except:
		log.log(3)
		fecthUrl[1] += 1
		server.addDelay(60, _autoGetGFWListThread, server)
		return
	domainConfig.config.resetGFWListDomain()
	for host in hostList:
		domainConfig.config.addGFWListDomain(host)
	domainConfig.config.save()
	server.addDelay(3600 * 6, _autoGetGFWListThread, server)

	
def _autoGetGFWListThread(server):
	sockConnect._connectPool.apply_async(_getGFWHost, server)

	
def autoGFWList(server, proxyPort):
	proxy = urllib.request.ProxyHandler({"http":"127.0.0.1:%d" % (proxyPort),
					"https":"127.0.0.1:%d" % (proxyPort)})
	opener = urllib.request.build_opener(proxy)
	urllib.request.install_opener(opener)
	server.addDelay(5, _autoGetGFWListThread, server)
