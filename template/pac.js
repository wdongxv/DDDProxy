function A(a, b) {
	return dnsDomainIs(a, b);
}
function B(a, b) {
	return shExpMatch(a, '*' + b + '*')
}
function FindProxyForURL(u, h) {
	if({% for domain in domainList %}A(h,"{{ domain }}")||{% end %}B(u, "get_real_ip_p")) {
		return "PROXY {{proxy_ddr}}; DIRECT";
	} else {
		return "DIRECT";
	}
}
