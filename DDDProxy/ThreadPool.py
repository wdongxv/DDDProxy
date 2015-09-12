# -*- coding: UTF-8 -*-
'''
Created on 2015年9月10日

@author: dxw
'''
from threading import Thread
from Queue import Queue
from DDDProxy import log


class Worker(Thread):
	def __init__(self, tasks):
		Thread.__init__(self)
		self.tasks = tasks
		self.start()
	def run(self):
		while True:
			try:
				func, args, kargs = self.tasks.get()
			except:
				pass
			try:
				func(*args, **kargs)
			except Exception, e:
				log.log(3)

class ThreadPool:
	def __init__(self, maxThread=20):
		self.tasks = Queue()
		self.maxThread = maxThread
		self.threadList = []
	def apply_async(self, func, *args, **kargs):
		self.tasks.put((func, args, kargs))
# 		log.log(2,"apply_async",
# 			threadList = len(self.threadList),
# 			maxThread=self.maxThread,
# 			tasks=self.tasks.qsize())
		if len(self.threadList) < self.maxThread and  len(self.threadList) < self.tasks.qsize():
			self.threadList.append(Worker(self.tasks))
		