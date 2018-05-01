# -*- coding: UTF-8 -*-
'''
Created on 2015年9月12日

@author: dxw
'''
import sys
import traceback
import time
import logging
from logging import DEBUG, INFO, WARNING, ERROR

_loglevel = 2

_logger = logging.getLogger()  
_logger.addHandler(logging.StreamHandler(sys.stderr) )  


def install(level=2,filename="/tmp/dddproxy.log"):
	global _loglevel
	_loglevel = level
	file_handler = logging.FileHandler(filename)
	_logger.addHandler(file_handler)  

	
def log(level, *args, **kwargs):
	global _loglevel
	if level < _loglevel:
		return
	
	data = "	".join(str(i) for i in args)
	data += "	".join("%s=%s" % (str(k), str(v)) for k, v in kwargs.items())
	if level == 3:
		data += "	" + str(sys.exc_info())
		try:
			data += "	" + str(traceback.format_exc())
		except:
			pass
	data = ["DEBUG", "INFO", "WARNING", "ERROR"][level] +"	"+ time.strftime("%y-%B-%d %H:%M:%S	") + data
	_logger.log([DEBUG, INFO, WARNING, ERROR][level] , data)
	

def cmp(a, b):
	return (a > b) - (a < b)


if __name__ == "__main__":
	install()
	log(3, "123")
	log(2, "123")
	log(1, "123")
	log(0, "123")
