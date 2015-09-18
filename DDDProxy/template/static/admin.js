$(document).ready(function(){
	function areaSetting(){
		return {
			animation:false,
			fillColor : {
				linearGradient : {
					x1 : 0,
					y1 : 0,
					x2 : 0,
					y2 : 1
				},
				stops : [[ 0, "#9DBFFF" ],
						[1,Highcharts.Color("#9DBFFF").setOpacity(0).get('rgba')]]
			},
			lineWidth : 1,
			lineColor : "#003066",
			marker : {
				enabled : false
			},
			shadow : false,
			states : {
				hover : {
					lineWidth : 1
				}
			},
			allowPointSelect : true,
			threshold : null
		};
	}

	var show = function(start,incoming,outgoing){
		var obj = $("#dataAnalysis");
		var chart = obj.highcharts();
		var incomingSeriesData = {
			pointInterval : 3600 * 1000,
			pointStart : start,
			name : 'incoming',
			data : incoming
		};
		var outgoingSeriesData = {
				pointInterval : 3600 * 1000,
				pointStart : start,
				name : 'outgoing',
				data : outgoing
			};
		
		if (chart !== undefined) {
			chart.hideLoading();
			chart.series[0].update(incomingSeriesData);
			chart.series[1].update(outgoingSeriesData);
			return
		}
		var startTime = start;
		var plotBands = [];
		var index = 0;
		for ( var i = 0; i < incoming.length;) {
			var startDate = new Date(startTime);
			var endTime = startTime + 3600000;
			if (startDate.getHours()==0) {
				plotBands.push({
					from : startTime,
					to : endTime,
					color : "RGBA(100,30,0,0.07)"
				});
			}
			index++;
			i++;
			startTime = endTime;
		}

		startTime = start;
		
		obj.highcharts({
			title : {
				text : "",
			},
			xAxis : {
				type : 'datetime',
				plotBands : plotBands
			// gridLineWidth:1,
			// gridLineColor:"#f0f0f0",
			},
			yAxis : {
				title : {
					enabled : false,
				},
				lineWidth : 1,
			},
			tooltip:{
				animation : false,
				shared : true,
				style : {
					fontSize : '14px',
				},
				formatter:function(){
					var d = new Date(this.x)
					var tmp = d.toLocaleDateString()+" "+d.getHours()+"点"+d.getMinutes()+"分<br/>";
					for ( var i in this.points) {
						var point = this.points[i];
						tmp += point.series.name+":"+IntToDataCount(point.y)+"<br/>"
					}
					return tmp;
				}
			},
			legend : {
				enabled : false
			},
			plotOptions : {
				area : areaSetting()
			},
			chart : {
				backgroundColor : "",
				type: 'spline'
			},
			credits : {
				enabled : false
			},
			series : [ incomingSeriesData,outgoingSeriesData ]
		});
	}
	
	/***************************/

	function echoName(domain,  status, times,index) {
		var statusStr = (status == 1 ? 'close' : 'open')
		f = '<div class="line" status="'+statusStr+'" index="'+index+'">'+
				'<div class="content"><div class="times"><p>'+(times<1000?times:IntToDataCount(times,1000))+'</p></div>'+
				'<div class="domain"><a class="domain_link" target="_blank" href="//'+ domain +'">'+domain+'</a></div></div>' +
				'<div class="optbox">'+
				'<a href="#" class="'+statusStr+'" >'+(status == 1 ? '⌧' : '⇄︎')+'</a>' +
				'<a href="#" class="delete">del</a>' +
				'</div>'+
				'</div>';
		return f;
	}
	var refreshDomainList = function(){
		proxyapi("domainList",null,function(data){
			var html = "";
			var domainList = data.domainList
			for(var i = 0; i < domainList.length;i++){
				var domain = domainList[i];
				html += echoName(domain.domain,domain.open,domain.connectTimes,i);
			}
			$("#proxyDomainList").html(html);
			$(".close,.open,.delete").click(function(){
				var cls = this.className;
				proxyapi("domainList",{"action":cls,"domain":$(this).parents(".line").find(".domain a").text()},function(){
					refreshDomainList();
				});
			})
		})
	}
	refreshDomainList();
	
	$("#newUrlSubmit").click(function(){
		var url = $("#newUrl")[0];
		proxyapi("addDomain",{"url":url.value},function(data){
			var newUrlInfo = $("#newUrlInfo")
			if(data.status == "ok"){
				url.value = "";
				newUrlInfo.text("");
				refreshDomainList();
			}else{
				newUrlInfo.text(url.value+" 错误的URL,末添加")
			}
		});
	})
	
	/***************************/
	
	
	var analysisDomain = null;
	var todayAnalysis = function(){
		var startTime = (new Date())/1000-3600*72;
		startTime -= startTime%3600;
		var today = new Date()
		today.setHours(0);
		today.setMinutes(0)
		today.setSeconds(0)
		proxyapi("analysisData",{"startTime":startTime,"todayStartTime":parseInt(today/1000),"domain":(analysisDomain?analysisDomain:"")},function(data){
			var analysisData = data.analysisData;
			show(startTime*1000,analysisData.outgoing,analysisData.incoming);
			
			var html = "";
			html += '<div class="dataCount"><span>24小时数据流量:</span>'+IntToDataCount(analysisData.countData)+'</div>';
			var list = analysisData.domainDataList;
			
			for(var i = 0; i < list.length;i++){
				var domain = list[i];
				html += '<div class="reusetDomainList">'+
					'<span class="reusetTimes">'+IntToDataCount(domain.dataCount)+'</span>'+
					'<a>'+domain.domain+'</a>'+
					'</div>';
			}
			html += '<div class="reusetDomainList" id="showall">显示全部</div>';
			
			$("#domainAnalysis").html(html);
			function showallbutton(){
				if(analysisDomain)
					$("#showall").show();
				else
					$("#showall").hide();
			}
			$("#domainAnalysis .reusetDomainList").click(function(){
				analysisDomain = $(this).find("a").text();
				showallbutton();
				var obj = $("#dataAnalysis");
				var chart = obj.highcharts();
				chart.showLoading();
				todayAnalysis();
			});
			showallbutton();
			
		});
	};
	setInterval(todayAnalysis,5000);
	todayAnalysis();
})