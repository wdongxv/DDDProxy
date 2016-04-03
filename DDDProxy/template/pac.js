function FindProxyForURL(url, host) {
	function matchDomain(a) {
		return dnsDomainIs(host, a);
	}
	function B(a) {
		return shExpMatch(url, '*' + a + '*');
	}
	function matchList(list){
		for(var i=0;i < list.length;i++){
			if(matchDomain(list[i])){
				return true;
			}
		}
		return false;
	}
	var domainWhiteList = {{domainWhiteListJson}};
	var domainList = {{domainListJson}};
	if(matchList(domainWhiteList)){
		return "DIRECT";
	}
	if(matchList(domainList)){
		return "SOCKS5 {{proxy_ddr}};PROXY {{proxy_ddr}};";
	}
	if(matchList(["status.dddproxy.com"])){
		return "PROXY {{proxy_ddr}};";
	}
	return "DIRECT";
}
