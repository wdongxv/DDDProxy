'''
Created on 2015-4-15

@author: dxw
'''
import httplib
import DDDProxyConfig
import urlfetch
import urllib2

proxy = urllib2.ProxyHandler({"http":"127.0.0.1:%d" % (DDDProxyConfig.localServerProxyListenPort), 
					"https":"127.0.0.1:%d" % (DDDProxyConfig.localServerProxyListenPort)})
opener = urllib2.build_opener(proxy)
urllib2.install_opener(opener)


print urllib2.urlopen('https://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt')

