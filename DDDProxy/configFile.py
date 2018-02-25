# -*- coding: UTF-8 -*-
'''
Created on 2015年9月5日

@author: dxw
'''
import json
import os
from __builtin__ import BaseException


class autoDataObject(dict):
	def __getitem__(self, key):
		if key not in self:
			item = autoDataObject()
			self[key] = item
		else:
			item = dict.__getitem__(self, key)
		return item

class configFile:
	def __init__(self):
		self.setting = None
		try:
			fp = open(self.getConfigfileFilePath(),"r")
			self.setting = json.load(fp,object_hook = autoDataObject)
			fp.close()
		except:
			pass
		if not self.setting:
			self.setting = {}
	def __getitem__(self,k):
		return self.setting[k] if k in self.setting else None
	def __setitem__(self,k,v):
		self.setting[k] = v;
		self.save()
	def save(self):
		fp = open(self.getConfigfileFilePath(),"w")
		json.dump(self.setting,fp)
		fp.close()
	def getConfigfileFilePath(self):
		raise NotImplementedError()
	@staticmethod
	def makeConfigFilePathName(name):
		dirName = os.path.expanduser('~')+"/.DDDProxy/"
		if not os.path.exists(dirName):
			os.makedirs(dirName)
		elif not os.path.isdir(dirName):
			raise BaseException(dirName+" not is dir!")
		return dirName+name