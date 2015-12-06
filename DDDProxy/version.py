import os

version = "3.0.1"


def update(server):
	
	os.system("git pull &")
	
	server.addDelay(3600*10, update)
