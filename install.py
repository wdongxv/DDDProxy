#!/usr/bin/env python3
from optparse import OptionParser
import sys
import os
import getpass
import string
import random
import platform



def pwGen(length):
	chars = string.ascii_letters + string.digits
	return ''.join([random.choice(chars) for _ in range(length)])

if __name__ == "__main__":
	parser = OptionParser("%s remoteServer|localServer" % (sys.argv[0]))
	if len(sys.argv) < 2 or not sys.argv[1] in ["remoteServer", "localServer"]:
		parser.print_help()
		exit(1)
	server = sys.argv[1]
	platformName = platform.system().lower()
	mainPath = os.path.dirname(__file__)
	mainPath = os.path.abspath(mainPath)
	startUpArgs = parser.parse_args()[0]
	
	print("install", server , "on", platformName)
	
	
	def setInitFile(tempFilePath, filePath, authFormat):
		f = open(tempFilePath, "r")
		InitFileContent = "" + f.read()
		f.close()

		port = input("Enter Bind Port(empty for default):")
		if not port:
			port = "-1"
		InitFileContent = InitFileContent.replace("{{python}}", sys.executable)
		InitFileContent = InitFileContent.replace("{{path-to-DDDProxy}}", mainPath)
		InitFileContent = InitFileContent.replace("{{port-setting}}", port)
		InitFileContent = InitFileContent.replace("{{entry-point}}", "%s.py" % (server))
		InitFileContent = InitFileContent.replace("{{server-name}}", "dddproxy.python3." + server)
		if server == "remoteServer":
			serverPassword = ""
			while True:
				serverPassword = getpass.getpass("Enter passphrase(empty for random):")
				if not serverPassword:
					serverPassword = pwGen(20)
					print("Server password:", serverPassword)
					break
				if serverPassword != getpass.getpass("Enter same passphrase again:"):
					print("Passphrases do not match. try again")
				else:
					break
			InitFileContent = InitFileContent.replace("{{auth}}", authFormat % (serverPassword))
		else:
			InitFileContent = InitFileContent.replace("{{auth}}", "")
		if os.path.exists(filePath):
			overwrite = input(filePath + " already exists.\nOverwrite (y/n)?")
			if overwrite != "y":
				exit(1)
		print("Write file ", filePath)
		f = open(filePath, "w+")
		f.write(InitFileContent)
		f.close()
		return port
	if platformName == "darwin":
# 		if server == "localServer":
		homedir = os.path.expandvars('$HOME')
		launchAgentsDir = homedir + "/Library/LaunchAgents"
		if not os.path.exists(launchAgentsDir):
			os.mkdir(launchAgentsDir)

		plistName = "dddproxy.python3." + server + ".plist"
		plistPath = launchAgentsDir + "/" + plistName
		port = setInitFile(mainPath + "/.install/mac.plist" , plistPath, "<string>--auth</string><string>%s</string>")
		
		print("try unload server ...")
		os.system("launchctl unload \"%s\"" % (plistPath))
		print("try start server ...")
		os.system("launchctl load \"%s\"" % (plistPath))
		
		if server == "localServer":
			openMPage = input("Open management page (y/n)?")
			if openMPage == "y":
				os.system("open http://127.0.0.1:%s" % ("8080" if port == "-1" else port))
		
		print("done!")
	elif platformName == "linux":
		release, version, _ = platform.dist()
		release = release.lower()
		if release == "centos":
			if version.startswith("7."):
				serverFile = "dddproxy_python3_" + server + ".service"
				setInitFile(mainPath + "/.install/centos7", "/usr/lib/systemd/system/" + serverFile, "--auth %s")
				os.system("systemctl enable " + serverFile)
				os.system("systemctl stop " + serverFile)
				os.system("systemctl start " + serverFile)
		elif release == "ubuntu" or release == "debian":
			serverFile = "dddproxy_python3_" + server + ""
			setInitFile(mainPath + "/.install/ubuntu", "/etc/init.d/" + serverFile, "--auth %s")
			os.system("chmod +x /etc/init.d/"+serverFile)
			os.system("update-rc.d %s defaults"%(serverFile))
			print("run this command line for start:")
			print ("")
			print ("sudo /etc/init.d/%s restart"%(serverFile))
			print ("")
	else:
		print("")
