# -*- coding: UTF-8 -*-
'''
Created on 2015年9月3日

@author: dxw
'''
import os
import select
import socket
import ssl
import threading
import time

from ThreadPool import ThreadPool
from configFile import configFile
from DDDProxy import log
import json
from datetime import datetime
import httplib



createCertLock = threading.RLock()
socket.setdefaulttimeout(5)
socketBufferMaxLenght = 1024*4


class sockConnect(object):
	"""
	@type sock: _socketobject
	"""
	
	_filenoLoop = 0
	
	def __init__(self,server):
		self.server = server
		self.info = {
					"startTime":int(time.time()),
					"send":0,
					"recv":0
					}
		self.makeAlive()
		self.sock = None
		self.address = (None,None)
		self.dataSendList = []
		sockConnect._filenoLoop+=1
		self._fileno = sockConnect._filenoLoop
		self.connectName = ""
	def makeAlive(self):
		self.info["lastAlive"] = int(time.time())
		
	def __str__(self, *args, **kwargs):
		return self.connectName if self.connectName else  ( self.filenoStr()+str(self.address))
	def filenoStr(self):
		return "["+str(self.fileno())+"]"
	
	def SSLLocalCertPath(self,remoteServerHost,remoteServerPort):
		return configFile.makeConfigFilePathName("%s-%d.pem"%(remoteServerHost,remoteServerPort))

	def fetchRemoteCert(self,remoteServerHost,remoteServerPort):
		ok = False
		createCertLock.acquire()
		try:
			if not os.path.exists(self.SSLLocalCertPath(remoteServerHost,remoteServerPort)):
				cert = ssl.get_server_certificate(addr=(remoteServerHost, remoteServerPort))
				open(self.SSLLocalCertPath(remoteServerHost,remoteServerPort), "wt").write(cert)
			ok = True
		except:
			log.log(3,remoteServerHost,remoteServerPort)
		createCertLock.release()
		return ok
	def _doConnectSock(self,address,useSsl=False,cb=None,setThreadName=None):
		ok = True
		try:
			sock = None
			setThreadName("connect %s:%s"%(address[0],address[1]))
			addr = (socket.gethostbyname(address[0]),address[1])
			if useSsl:
				if self.fetchRemoteCert(address[0], address[1]):
					sock = ssl.wrap_socket(
								sock	=		socket.socket(socket.AF_INET, socket.SOCK_STREAM),
								ca_certs	=	self.SSLLocalCertPath(address[0], addr[1]),
								cert_reqs	=	ssl.CERT_REQUIRED)
			else:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

			if sock:
				sock.connect(addr)
			else:
				ok = False
		except:
			log.log(3,address)
			ok = False
		if ok:
			self.server.addCallback(self._setConnect,sock,address)
		else:
			self.server.addCallback(self.onClose)
		if cb:
			self.server.addCallback(cb,self if ok else None)
	connectPool = ThreadPool(maxThread=100)
	def connect(self,address,useSsl=False,cb=None):
		"""
		@param address: 仅记录
		"""
		address = address
		sockConnect.connectPool.apply_async(self._doConnectSock,address,useSsl,cb)
# 		thread.start_new_thread(self._doConnectSock,())
	def _setConnect(self,sock,address):
		"""
		@type sock: _socketobject
		"""
		self.sock = sock
		self.address = address
		self.onConnected()
	
	def fileno(self):
		return self._fileno
	
	def send(self,data):
		if data and len(data)>socketBufferMaxLenght:
			self.dataSendList.append(data[:socketBufferMaxLenght])
			self.send(data[socketBufferMaxLenght:])
		else:
			self.dataSendList.append(data)
	def onConnected(self):
		self.server.addSockConnect(self)
		
	def onRecv(self,data):
# 		log.log(2,self,"<<",repr(data))
		self.info["recv"] += len(data)
		self.makeAlive()
	
	def pauseRecvAndSend(self):
		return False
	
	def onSend(self,data):
		self.info["send"] += len(data)
		l = self.sock.send(data)
# 		log.log(2,self,">>",len(data),l)
		self.makeAlive()
	def onClose(self):
		pass
	def close(self):
		self.send(None)
		
		
		
		
	def makeReseponse(self,data, ContentType="text/html", code=200,connection="close",header={}):	
		def httpdate():
			dt = datetime.now();
			weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
			month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
					"Oct", "Nov", "Dec"][dt.month - 1]
			return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
		        dt.year, dt.hour, dt.minute, dt.second)
		if type(data) is unicode:
			data = data.encode("utf-8")
		elif not type(data) is str:
			data = json.dumps(data)
			ContentType = "application/json"
		httpMessage = ""
		httpMessage += "HTTP/1.1 " + str(code) + " " + (httplib.responses[code]) + "\r\n"
		httpMessage += "Server: DDDProxy/2.0\r\n"
		httpMessage += "Date: " + httpdate() + "\r\n"
		httpMessage += "Content-Length: " + str(len(data)) + "\r\n"
		httpMessage += "Content-Type: " + ContentType + "\r\n"
		httpMessage += "Connection: " +connection + "\r\n"
		for k,v in header.items():
			httpMessage += k+": " +v + "\r\n"
		httpMessage += "\r\n"
		httpMessage += data
		return httpMessage
	
	def reseponse(self, data, ContentType="text/html", code=200,connection="close",header={}):
		self.send(self.makeReseponse(data, ContentType, code,connection,header))

class baseServer():
	def __init__(self,handler):
		self.handler = handler

		self._socketConnectList = {}
		self.serverList = []

		self.callbackList = []

		socket.setdefaulttimeout(10)

	def addCallback(self,cb, *args, **kwargs):
		self.callbackList.append((cb,0,args,kwargs))
	def addDelay(self,delay,cb, *args, **kwargs):
		self.callbackList.append((cb,delay+time.time(),args,kwargs))
		
	def addListen(self,port,host=""):
# 		self.server = bind_sockets(port=self.port, address=self.host) 
		log.log(1,"run in ",host,":",port)
		server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		
		server.bind((host, port))
		server.listen(1024)
		self.addSockListen(server)
	def addSockListen(self,sock):
		"""
		@param sock: _socketobject
		"""
		sock.setblocking(False)
		self.serverList.append(sock)
		
	def addSockConnect(self,connect):
		if not connect.sock in self._socketConnectList:
			connect.sock.setblocking(False)
			try:
				connect.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
			except:
				pass
			
			connect.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
			connect.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
			try:
				TCP_KEEPALIVE = 0x10
				connect.sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 3)
			except:
				pass
			self._socketConnectList[connect.sock] = connect
	

	def start(self):
		
		while True:
			rlist = []+self.serverList
			wlist = []
			currentTime = time.time()
			for connect in self._socketConnectList.values():
				if connect.pauseRecvAndSend():
					continue
				rlist.append(connect.sock)
				if len(connect.dataSendList)>0:
					wlist.append(connect.sock)
				elif connect.info["lastAlive"] < currentTime-3600:
					connect.close()
				
			try:
				s_readable,s_writable,s_exceptional = select.select(rlist, wlist, rlist,1)
			except:
				log.log(3)
				continue;
			timeCheck = []
			timeCheck.append(("start",time.time()))
			for sock in s_readable:
				if sock in self.serverList:
					self.onConnect(sock)
				else:
					self.onData(sock)
					timeCheck.append(("read",time.time(),sock))
			for sock in s_writable:
				self.onSend(sock)
				timeCheck.append(("write",time.time(),sock))
			for sock in s_exceptional:
				self.onExcept(sock)
				timeCheck.append(("except",time.time(),sock))
				
			cblist = self.callbackList
			self.callbackList = []
			currentTime = time.time()
			for cbobj in cblist:
				if cbobj[1] <= currentTime:
					cbobj[0](*cbobj[2],**cbobj[3])
				else:
					self.callbackList.append(cbobj)
				timeCheck.append(("callback",time.time(),cbobj))
			
			lastCheck = None
			for check in timeCheck:
				if lastCheck:
					usetime = check[1] - lastCheck[1]
					if usetime >1:
						log.log(3,check[0],"usetime > 1.0s",usetime,check[2])
				lastCheck = check
	def onConnect(self,sock):
		sock,address = sock.accept()
		connect = self.handler(server=self)
		connect._setConnect(sock, address)
		log.log(2,connect,"*	connect")
		
	def onSend(self,sock):
		if sock in self._socketConnectList:
			connect = self._socketConnectList[sock]
			data = connect.dataSendList.pop(0)
			if data:
				try:
					connect.onSend(data)
					return
				except:
					log.log(3)
			sock.close()
			self.onExcept(sock)
			
	def onData(self,sock):
		
		data = None
		
		try:
			data = sock.recv(socketBufferMaxLenght)
		except ssl.SSLError as e:
			if e.errno == 2:
				return
			log.log(3)
		except:
			log.log(3)
		
		if data:
			if isinstance(sock, ssl.SSLSocket):
				while 1:
					data_left = sock.pending()
					if data_left:
						data += sock.recv(data_left)
					else:
						break
			if sock in self._socketConnectList:
				handler = self._socketConnectList[sock]
				handler.onRecv(data)
		else:
			self.onExcept(sock)
	def onExcept(self,sock):
		if sock in self._socketConnectList:
			handler = self._socketConnectList[sock]
			log.log(2,handler,"<	close")
			del self._socketConnectList[sock]
			handler.onClose()
	def dumpConnects(self):
		connects = {}
		for handler in self._socketConnectList.values():
			connect = handler.address[0]
			if not connect in connects:
				connects[connect] = []
			info = {"name":str(handler)}
			info.update(handler.info)
			connects[connect].append(info)
		
		for l in connects.values():
			l.sort(cmp=lambda x, y : cmp(y["send"] + y["recv"], x["send"] + x["recv"]))
		
		return {"connect":connects,"threads":sockConnect.connectPool.dump(),"currentTime":int(time.time())}
	

def get_mime_type(filename):
	filename_type = os.path.splitext(filename)[1][1:]
	type_list = {
	'html' : 'text/html',
	'htm' : 'text/html',
	'shtml' : 'text/html',
	'css' : 'text/css',
	'xml' : 'text/xml',
	'gif' : 'image/gif',
	'jpeg' : 'image/jpeg',
	'jpg' : 'image/jpeg',
	'js' : 'application/x-javascript',
	'atom' : 'application/atom+xml',
	'rss' : 'application/rss+xml',
	'mml' : 'text/mathml',
	'txt' : 'text/plain',
	'jad' : 'text/vnd.sun.j2me.app-descriptor',
	'wml' : 'text/vnd.wap.wml',
	'htc' : 'text/x-component',
	'png' : 'image/png',
	'tif' : 'image/tiff',
	'tiff' : 'image/tiff',
	'wbmp' : 'image/vnd.wap.wbmp',
	'ico' : 'image/x-icon',
	'jng' : 'image/x-jng',
	'bmp' : 'image/x-ms-bmp',
	'svg' : 'image/svg+xml',
	'svgz' : 'image/svg+xml',
	'webp' : 'image/webp',
	'jar' : 'application/java-archive',
	'war' : 'application/java-archive',
	'ear' : 'application/java-archive',
	'hqx' : 'application/mac-binhex40',
	'doc' : 'application/msword',
	'pdf' : 'application/pdf',
	'ps' : 'application/postscript',
	'eps' : 'application/postscript',
	'ai' : 'application/postscript',
	'rtf' : 'application/rtf',
	'xls' : 'application/vnd.ms-excel',
	'ppt' : 'application/vnd.ms-powerpoint',
	'wmlc' : 'application/vnd.wap.wmlc',
	'kml' : 'application/vnd.google-earth.kml+xml',
	'kmz' : 'application/vnd.google-earth.kmz',
	'7z' : 'application/x-7z-compressed',
	'cco' : 'application/x-cocoa',
	'jardiff' : 'application/x-java-archive-diff',
	'jnlp' : 'application/x-java-jnlp-file',
	'run' : 'application/x-makeself',
	'pl' : 'application/x-perl',
	'pm' : 'application/x-perl',
	'prc' : 'application/x-pilot',
	'pdb' : 'application/x-pilot',
	'rar' : 'application/x-rar-compressed',
	'rpm' : 'application/x-redhat-package-manager',
	'sea' : 'application/x-sea',
	'swf' : 'application/x-shockwave-flash',
	'sit' : 'application/x-stuffit',
	'tcl' : 'application/x-tcl',
	'tk' : 'application/x-tcl',
	'der' : 'application/x-x509-ca-cert',
	'pem' : 'application/x-x509-ca-cert',
	'crt' : 'application/x-x509-ca-cert',
	'xpi' : 'application/x-xpinstall',
	'xhtml' : 'application/xhtml+xml',
	'zip' : 'application/zip',
	'bin' : 'application/octet-stream',
	'exe' : 'application/octet-stream',
	'dll' : 'application/octet-stream',
	'deb' : 'application/octet-stream',
	'dmg' : 'application/octet-stream',
	'eot' : 'application/octet-stream',
	'iso' : 'application/octet-stream',
	'img' : 'application/octet-stream',
	'msi' : 'application/octet-stream',
	'msp' : 'application/octet-stream',
	'msm' : 'application/octet-stream',
	'mid' : 'audio/midi',
	'midi' : 'audio/midi',
	'kar' : 'audio/midi',
	'mp3' : 'audio/mpeg',
	'ogg' : 'audio/ogg',
	'm4a' : 'audio/x-m4a',
	'ra' : 'audio/x-realaudio',
	'3gpp' : 'video/3gpp',
	'3gp' : 'video/3gpp',
	'mp4' : 'video/mp4',
	'mpeg' : 'video/mpeg',
	'mpg' : 'video/mpeg',
	'mov' : 'video/quicktime',
	'webm' : 'video/webm',
	'flv' : 'video/x-flv',
	'm4v' : 'video/x-m4v',
	'mng' : 'video/x-mng',
	'asx' : 'video/x-ms-asf',
	'asf' : 'video/x-ms-asf',
	'wmv' : 'video/x-ms-wmv',
	'avi' : 'video/x-msvideo'
	}
	if ( filename_type in type_list.keys() ):
		return type_list[filename_type]
	else:
		return ''	

if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()
