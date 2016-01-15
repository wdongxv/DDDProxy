(function() {
	var clientId = '617529453372-t2ngei0uk2fqh8rh8hvlak9qh9bkla6q.apps.googleusercontent.com';
	var scopes = 'https://www.googleapis.com/auth/drive.appdata';

	var status = $("#backupStatus")
	var statusTimer = null;
	function statusText(text) {
		status.text("("+text+")")
		if (statusTimer)
			clearTimeout(statusTimer)
		statusTimer = setTimeout(function() {
			status.text("")
		}, 5000)
	}
	function loadDrive(cb) {
		function authGoogle(cb) {
			function handleAuthResult(authResult) {
				if (authResult && !authResult.error) {
					cb();
				} else {
					statusText("链接Google失败");
					cb("error");
				}
			}
			statusText("链接Google中...");
			gapi.auth.authorize({
				client_id : clientId,
				scope : scopes,
				immediate : false
			}, handleAuthResult);
		}

		authGoogle(function(err) {
			if (err) {
				return cb(err);
			}
			statusText("加载云端硬盘引擎");
			gapi.client.load('drive', 'v3', function(err) {
				cb();
			});
		})
	}
	function updateFile(fileId, fileMetadata, fileData, callback) {
		const
		boundary = '-------314159265358979323846';
		const
		delimiter = "\r\n--" + boundary + "\r\n";
		const
		close_delim = "\r\n--" + boundary + "--";

		var contentType = 'application/octect-stream';
		var base64Data = btoa(fileData);
		var multipartRequestBody = delimiter + 'Content-Type: application/json\r\n\r\n' + JSON.stringify(fileMetadata) + delimiter + 'Content-Type: ' + contentType + '\r\n'
				+ 'Content-Transfer-Encoding: base64\r\n' + '\r\n' + base64Data + close_delim;

		var request = gapi.client.request({
			'path' : '/upload/drive/v2/files/' + fileId,
			'method' : 'PUT',
			'params' : {
				'uploadType' : 'multipart',
				'alt' : 'json'
			},
			'headers' : {
				'Content-Type' : 'multipart/mixed; boundary="' + boundary + '"'
			},
			'body' : multipartRequestBody
		});
		if (!callback) {
			callback = function(file) {
				console.log(file)
			};
		}
		request.execute(callback);
	}
	function downloadFile(id, link, callback) {
		var drive = gapi.client.drive
		var req = gapi.client.request({
			'method' : 'GET',
			path : "/drive/v2/files/" + id + "?alt=media"
		})
		req.then(callback);
		req = null
	}
	function getConfigFileId(cb) {
		var drive = gapi.client.drive
		var request = drive.files.list({
			spaces : 'appDataFolder',
			'pageSize' : 100,
			'q' : "name='config.txt'",
			'fields' : "nextPageToken, files(id, name,webContentLink)"
		}).execute(function(resp) {

			var files = resp.files;
			if (!files) {
				return;
			}
			if (files.length > 0) {
				for (var i = 1; i < files.length; i++) {
					drive.files['delete']({
						spaces : 'appDataFolder',
						"fileId" : files[i].id
					}).execute(function(resp) {
						resp = null;
					})
				}
				cb(files[0].id, files[0].webContentLink)
			} else {
				var request = drive.files.create({
					resource : {
						'name' : 'config.txt',
						mimeType : 'text/json',
						'parents' : [ 'appDataFolder' ]
					}
				}).execute(function(err, resp) {
					resp = null
				});
			}
		});
	}
	$("#backup,#restore,#replaceRestore").click(function() {
		var opt = this.id;
		loadDrive(function() {
			var drive = gapi.client.drive
			getConfigFileId(function(id, link) {
				if (id) {
					if (opt == "backup") {
						statusText("拉取配置列表...");

						proxyapi("domainList", null, function(data) {
							var backupList = []

							for (var i = 0; i < data.domainList.length; i++) {
								var domain = data.domainList[i];
								backupList.push([ domain.domain, domain.open ])
							}
							updateFile(id, {}, JSON.stringify(backupList), function(err, file) {
								statusText("备份" + (err.message ? err.message : "成功"));
							})
						})

					} else {
						statusText("从Google下载地址列表...");
						downloadFile(id, link, function(resp) {
							if (resp.status == 200) {
								var clearAll = (opt == "replaceRestore")
								var info = (clearAll ? "完全清除 和 " : "") + "恢复地址列表"
								statusText(info + "...");
								proxyapi("restore", {
									"domainList" : resp.result,
									"clearAll" : clearAll
								}, function(data) {
									refreshDomainList();
									statusText(info + " " + data.status);
								});
							} else {
								statusText("从Google下载地址列表失败");
							}
						})
					}
				}
			})
		})

	})

	window.onGoogleClientLoadCallback = function() {
		$("#backupBox").show()
		gapi.client.setApiKey("AIzaSyC1aZR9-6Dhm0jszLOWWU1ZdZH53zfQF9A");
	}

})()