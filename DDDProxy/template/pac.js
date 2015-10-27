function FindProxyForURL(url, host) {
	function A(a) {
		return dnsDomainIs(host, a);
	}
	function B(a) {
		return shExpMatch(url, '*' + a + '*')
	}
	if( {{domainList}} A("status.dddproxy.com")) {
		return "PROXY {{proxy_ddr}}; DIRECT";
	} else {
		return "DIRECT";
	}
}
