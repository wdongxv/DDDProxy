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
	domainList.push("status.dddproxy.com");
	if(matchList(domainWhiteList)){
		return "DIRECT";
	}
	if(matchList(domainList)){
		return "PROXY {{proxy_ddr}}; DIRECT";
	}
	return "DIRECT";
}
