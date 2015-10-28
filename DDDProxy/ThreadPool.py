# -*- coding: UTF-8 -*-
'''
Created on 2015年9月10日

@author: dxw
'''
from threading import Thread
from Queue import Queue
from DDDProxy import log
import time


class ThreadPoolWorker(Thread):
	def __init__(self, tasks):
		Thread.__init__(self)
		self.tasks = tasks
		self.start()
		self.runing = False
		self.startTime = -1
	def run(self):
		while True:
			try:
				self.setName("waitingLoop")
				self.runing = False
				func, args, kargs = self.tasks.get()
			except:
				pass
			try:
				self.startTime = int(time.time())
				self.runing = True
				kargs["setThreadName"]=self.setName
				func( *args, **kargs)
			except:
				log.log(3)

class ThreadPool:
	def __init__(self, maxThread=20):
		self.tasks = Queue()
		self.maxThread = maxThread
		self.threadList = []
	def dump(self):
		infos = []
		for thread in self.threadList:
			if thread.runing:
				infos.append({"startTime":thread.startTime,"name":thread.name})
		return infos
	def apply_async(self, func, *args, **kargs):
		self.tasks.put((func, args, kargs))
		if len(self.threadList) < self.maxThread and  len(self.threadList) < self.tasks.qsize():
			self.threadList.append(ThreadPoolWorker(self.tasks))
		