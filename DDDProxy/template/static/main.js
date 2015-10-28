function proxyapi(opt, data, callback, url) {
	var xhr = new XMLHttpRequest();
	if (!data)
		data = {};
	if (!url)
		url = "/"
	xhr.open("POST", url, true);
	xhr.onreadystatechange = function(e) {
		if (xhr.readyState == 4) {
			var json = null;
			try {
				if (xhr.status == 200)
					json = JSON.parse(xhr.responseText);
			} catch (e) {
			}
			callback(json);
		}
	};
	var post = {
		opt : opt
	};
	for ( var i in data) {
		post[i] = data[i];
	}
	xhr.send(JSON.stringify(post));
}
function IntToDataCount(dataCount, jinzhi) {
	if (!jinzhi)
		jinzhi = 1024.0;
	var unit = 0;
	while (dataCount > jinzhi) {
		dataCount = dataCount / jinzhi;
		unit++;
	}
	var units = [ "B", "K", "M", "G", "T" ];
	var list = ("" + dataCount).split(".")

	return (list.length > 1 ? (list[0] + '.' + list[1].substr(0, 1)) : list[0])
			+ units[unit];
}

function dumpdataParse(data) {
	var threads = data.threads;
	var connectList = data.connect
	var html = "";
	var connectCount = 0

	if (threads && threads.length) {
		html += "<div class='clientAddr'>thread pool</div>"
		html += "<div class='client'>";
		for (var j = 0; j < threads.length; j++) {
			var thread = threads[j]
			html += "<div class='connect'>"
					+ "<span class='connectInfo'>" + thread.name + " "
					+ (data.currentTime - thread.lastAlive) + "s</span>"
					+ "</div>"
		}
		html += "</div>"
	}

	for ( var i in connectList) {
		var remoteConnectList = connectList[i];
		var clientConectHtml = ""
		for (var j = 0; j < remoteConnectList.length; j++) {
			var connect = remoteConnectList[j]
			clientConectHtml += "<div class='connect'>"
					+ "<span class='send'>↾" + IntToDataCount(connect.send)
					+ "</span>" + "<span class='recv'>⇃"
					+ IntToDataCount(connect.recv) + "</span>"
					+ "<span class='connectInfo'>" + connect.name + " "
					+ (data.currentTime - connect.lastAlive) + "s</span>"
					+ "</div>"
		}

		connectCount += remoteConnectList.length

		html += "<div class='clientAddr'>" + i + " count("
				+ remoteConnectList.length + ")</div>"
		html += "<div class='client'>";
		html += clientConectHtml
		html += "</div>"
	}

	return [ html, connectCount ];
}

function getRemoteStatus(host, port, cb) {
	proxyapi("status", {
		"host" : host,
		"port" : port,
	}, cb, "http://" + host + port + "." + "status.dddproxy.com/");

}