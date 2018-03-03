# -*- coding: UTF-8 -*-
'''
Created on 2015年9月12日

@author: dxw
'''
import sys
import traceback
import time
import logging

debuglevel = 3

def log(level, *args, **kwargs):
	if level < debuglevel:
		return
	
	data = "	".join(str(i) for i in args)
	data += "	".join("%s=%s" % (str(k), str(v)) for k, v in kwargs.items())
	if level == 3:
		data += "	" + str(sys.exc_info())
		try:
			data += "	" + str(traceback.format_exc())
		except:
			pass
	data = time.strftime("%y-%B-%d %H:%M:%S:	") + data
	sys.stderr.write(["DEBUG", "INFO", "WARNING", "ERROR"][level] +":	" + data + "\n")

def cmp(a,b):
	return (a>b)-(a<b)

if __name__ == "__main__":
	log(3, "123")
	log(2, "123")
	log(1, "123")
	log(0, "123")
	
	
	
