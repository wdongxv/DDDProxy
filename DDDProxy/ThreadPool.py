# -*- coding: UTF-8 -*-
'''
Created on 2015年9月10日

@author: dxw
'''
from threading import Thread
from Queue import Queue
import logging


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
				logging.error(e)

class ThreadPool:
	def __init__(self, maxThread=20):
		self.tasks = Queue()
		self.maxThread = maxThread
		self.threadList = []
	def apply_async(self, func, *args, **kargs):
		self.tasks.put((func, args, kargs))
		if len(self.threadList) < self.maxThread:
			self.threadList.append(Worker(self.tasks))
		