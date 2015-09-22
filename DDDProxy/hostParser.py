import urlparse
import re

	
def parserUrlAddrPort(path):
	url=urlparse.urlparse(path)
	hostname = url.netloc
	port = "443" if url.scheme == "https" else "80"
	if hostname.find(':') > 0:
		addr,port = hostname.split(':')
	else:
		addr = hostname
	port = int(port)
	return (addr,port)

#^(.*?)\.*([^\.]+)(\.(?:net\.cn|com\.cn|com\.hk|co\.jp|org\.cn|[^\.\d]{2,3}))$
hostMatch = re.compile('^(.*?)\.*([^\.]+)(\.(?:(?:gov|org|com|co|net|edu)\.[a-z]{2,3}|[a-z]{2,3}))$')
def getDomainName(host):
	match = hostMatch.match(host)
	if match:
		hostGroup = match.groups()
		if len(hostGroup) > 2:
			return "%s%s" % (hostGroup[1], hostGroup[2])
	return None