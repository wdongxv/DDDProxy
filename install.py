#!/usr/bin/env python
from optparse import OptionParser
import sys
import os
from __builtin__ import file
import getpass
import string
import random
import platform

# echo "Install ..."
# current="$(dirname ${0})";
# cd $current
# root?Dir=$(dirname $(pwd))

# 
# plist=$(cat "$(pwd)/com.wangdongxu.ddproxy.plist")
# plist=${plist/path-to-DDDProxy/$rootDir}
# 
# 
# echo "Install $plistPath ..."
# echo $plist > $plistPath
# 
# echo "Starting ..."
#  $plistPath
# sleep 1
# url="8080"
# echo "open $url"
# open $url

# echo "Started !"
def pwGen(length):
	chars = string.ascii_letters + string.digits
	return ''.join([random.choice(chars) for _ in range(length)])

if __name__ == "__main__":
	parser = OptionParser("%s remoteServer|localServer [options]" % (sys.argv[0]))
	parser.add_option("-p", "--port", help="bind port" , default=-1)
	if len(sys.argv) < 2 or not sys.argv[1] in ["remoteServer", "localServer"]:
		parser.print_help()
		exit(1)
	server = sys.argv[1]
	platformName = platform.system().lower()
	mainPath = os.path.dirname(__file__)
	mainPath = os.path.abspath(mainPath)
	startUpArgs = parser.parse_args()[0]
	
	print "install", server , "on", platformName
	
	
	def setInitFile(tempFilePath, filePath, authFormat):
		f = file(tempFilePath, "r")
		InitFileContent = "" + f.read()
		f.close()
		
		InitFileContent = InitFileContent.replace("{{python}}", sys.executable)
		InitFileContent = InitFileContent.replace("{{path-to-DDDProxy}}", mainPath)
		InitFileContent = InitFileContent.replace("{{port-setting}}", str(startUpArgs.port))
		InitFileContent = InitFileContent.replace("{{entry-point}}", "%s.py" % (server))
		InitFileContent = InitFileContent.replace("{{server-name}}", "dddproxy." + server)
		if server == "remoteServer":
			serverPassword = ""
			while True:
				serverPassword = getpass.getpass("Enter passphrase(empty for random):")
				if not serverPassword:
					serverPassword = pwGen(20)
					print "Server password:", serverPassword
					break
				if serverPassword != getpass.getpass("Enter same passphrase again:"):
					print "Passphrases do not match. try again"
				else:
					break
			InitFileContent = InitFileContent.replace("{{auth}}", authFormat % (serverPassword))
		else:
			InitFileContent = InitFileContent.replace("{{auth}}", "")
		if os.path.exists(filePath):
			overwrite = raw_input(filePath + " already exists.\nOverwrite (y/n)?")
			if overwrite != "y":
				exit(1)
		print "Write file ", filePath
		f = file(filePath, "w+")
		f.write(InitFileContent)
		f.close()
		
	if platformName == "darwin":
# 		if server == "localServer":
		homedir = os.path.expandvars('$HOME')
		launchAgentsDir = homedir + "/Library/LaunchAgents"
		if not os.path.exists(launchAgentsDir):
			os.mkdir(launchAgentsDir)

		plistName = "dddproxy." + server + ".plist"
		plistPath = launchAgentsDir + "/" + plistName
		setInitFile(mainPath + "/.install/mac.plist" , plistPath, "<string>--auth</string><string>%s</string>")
		
		print "try unload server ..."
		os.system("launchctl unload \"%s\"" % (plistPath))
		print "try start server ..."
		os.system("launchctl load \"%s\"" % (plistPath))
		
		if server == "localServer":
			openMPage = raw_input("Open management page (y/n)?")
			if openMPage == "y":
				os.system("open http://127.0.0.1:%s" % ("8080" if startUpArgs.port == -1 else startUpArgs.port))
		
		print "done!"
	elif platformName == "linux":
		release, version, _ = platform.dist()
		if release == "centos":
			if version.startswith("7."):
				serverFile = "dddproxy_" + server + ".service"
				setInitFile(mainPath + "/.install/centos7", "/usr/lib/systemd/system/" + serverFile, "--auth %s")
				os.system("systemctl enable " + serverFile)
				os.system("systemctl stop " + serverFile)
				os.system("systemctl start " + serverFile)
		elif release == "debian":
			pass
	else:
		print ""
