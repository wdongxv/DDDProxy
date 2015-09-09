# -*- coding: UTF-8 -*-
'''
Created on 2015年9月8日

@author: dxw
'''
from configFile import configFile
import time
class domainConfig(configFile):
    defaultDomainList = ["google.com","gstatic.com","googleusercontent.com","googleapis.com","googleusercontent.com",
                        "googlevideo.com","facebook.com","youtube.com","akamaihd.net","ytimg.com","twitter.com",
                        "feedly.com","github.com","wikipedia.org","fbcdn.net","blogspot.com","t.co","ggpht.com",
                        "twimg.com","facebook.net","blogger.com","flickr.com","gmail.com","stackoverflow.com",
                        "gravatar.com","gmail.com","wikimedia.org","v2ex.com"]
    def __init__(self):
        configFile.__init__(self)
        if not self.setting:
            for domain in self.defaultDomainList:
                self.addDomain(domain)
            self.save()
    def getConfigfileFilePath(self):
        return "/tmp/pacDomainConfig.json"

    def getDomainOpenedList(self):
        pacList = []
        domainList = self.getDomainListWithAnalysis()
        for domain in domainList:
            if domain["open"]:
                pacList.append(domain["domain"])
        return pacList
    def getDomainListWithAnalysis(self):
        data = [{"domain":key,"open":value["open"],"connectTimes":value["connectTimes"]} for (key,value) in self.setting.items()]
        def sortDomainList(x,y):
            return x["connectTimes"]>y["connectTimes"];
        data.sort(cmp=lambda x,y : cmp(y["connectTimes"],x["connectTimes"]))
        return data;
    def removeDomain(self,domain):
        if domain in self.setting:
            del self.setting[domain]
            return True
        return False
    def closeDomain(self,domain):
        if domain in self.setting:
            self.setting[domain]["open"] = False
            return True
        return False
    def openDomain(self,domain):
        if domain in self.setting:
            self.setting[domain]["open"] = True
            return True
        return False
    def addDomain(self,domain,formGwflist = False):
        if not domain in self.setting:
            self.setting[domain] = {"connectTimes":0,"open":True,"formGwflist":formGwflist,"createTime":time.time()}
            return True
        else:
            currentDomain = self.setting[domain];
            if formGwflist:
                if currentDomain["connectTimes"]==0 and currentDomain["formGwflist"] and time.time()-currentDomain["createTime"] > 3600*24*30:
                    currentDomain["open"] = False
                    return True
            else:
                currentDomain["open"] = True
        return False
    def domainConnectTimes(self,domain,times):
        if domain in self.setting:
            data = self.setting[domain]
            data["connectTimes"] += times

config = domainConfig()