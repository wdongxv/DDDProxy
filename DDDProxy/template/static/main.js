function proxyapi(opt, data, callback) {
	var xhr = new XMLHttpRequest();
	if (!data)
		data = {};
	xhr.open("POST", "/", true);
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
function IntToDataCount(dataCount,jinzhi){
	if(!jinzhi)
		jinzhi = 1024.0;
	var unit = 0;
	while (dataCount>jinzhi){
		dataCount = dataCount/jinzhi;
		unit++;
	}
	var units = ["B","K","M","G","T"];
	var list = (""+dataCount).split(".")
	
	return (list.length>1?(list[0]+'.'+list[1].substr(0,1)):list[0])+units[unit];
}