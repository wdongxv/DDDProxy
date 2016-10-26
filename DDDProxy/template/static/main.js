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
var timeUnits = ["s","m","h"]
function IntToDataCount(dataCount, jinzhi, units) {
	if (!jinzhi)
		jinzhi = 1024.0;
	var unit = 0;
	if (!units)
		units = [ "B", "K", "M", "G", "T" ];
	while (Math.abs(dataCount) > jinzhi && unit < units.length - 1) {
		dataCount = dataCount / jinzhi;
		unit++;
	}
	var list = ("" + dataCount).split(".")

	return dataCount.toFixed(unit >= 1 ? 1 : 0) + units[unit];
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
			html += "<div class='connect'>" + "<span class='connectInfo'>" + thread.name + " " + (data.currentTime - thread.startTime) + "s</span>" + "</div>"
		}
		html += "</div>"
	}
	var allKey = []
	for ( var i in connectList) {
		allKey.push(i)
	}
	allKey.sort()

	for (var i = 0; i < allKey.length; i++) {
		var remoteConnectList = connectList[allKey[i]];
		var clientConectHtml = ""
		for (var j = 0; j < remoteConnectList.length; j++) {
			var connect = remoteConnectList[j]
			clientConectHtml += "<div class='connect'>" 
				+ "<span class='send'>↾" + IntToDataCount(connect.send) + "</span>" 
				+ "<span class='recv'>⇃" + IntToDataCount(connect.recv) + "</span>"
				+ "<span class='connectInfo'>" + connect.name + " "
				+ (connect.pingSpeed ? ("ping " + IntToDataCount(data.currentTime - connect.lastPingSendTime,60,timeUnits) + " ttl " + (connect.pingSpeed * 1000).toFixed(1) + "ms") : "") + "</span>"
				+ "<span class='lastUpdatetime'>"+IntToDataCount(data.currentTime - Math.max(connect.lastSendTime,connect.lastRecvTime), 60, timeUnits) + "</span>" 
				+ "</div>";
		}

		connectCount += remoteConnectList.length

		html += "<div class='clientAddr'>" + allKey[i] + " count(" + remoteConnectList.length + ")</div>"
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