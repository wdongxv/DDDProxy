function proxyapi(opt, data, callback) {
	var xhr = new XMLHttpRequest();
	if (!data)
		data = {};
	xhr.open("POST", "", true);
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