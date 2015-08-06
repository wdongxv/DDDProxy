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
	function isLeapyear(year) {
		return (year % 4 == 0) && (year % 100 != 0 || year % 400 == 0); // 四年一闰，百年不闰，四百年再闰
	}

	function dateDaysCountOfMonth(year, month) {
		switch (month) {
		case 4:
		case 6:
		case 9:
		case 11:
			return 30;
		case 2:
			return isLeapyear(year) ? 29 : 28;
		default:
			break;
		}
		return 31;
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
// for ( var i = 0; i < data.length; i++) {
// var startDate = new Date(startTime);
// if (startDate.getDay() == 6) {
// plotBands.push({
// from : startTime,
// to : startTime + 86400000,
// color : "RGBA(100,30,0,0.07)"
// });
// }
// startTime += 86400000;
// }

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
		/* obj[0].charts = charts; */

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

	function echoName(domain,  status, times,index) {
		var statusStr = (status == 1 ? 'close' : 'open')
		f = '<div class="line" status="'+statusStr+'" index="'+index+'">'+
				'<div class="content"><div class="times"><p>'+(times<1000?times:IntToDataCount(times,1000))+'</p></div>'+
				'<div class="domain"><a class="domain_link" target="_blank" href="//'+ domain +'">'+domain+'</a></div></div>' +
				'<div class="optbox">'+
				'<a href="?opt='+statusStr+'&domain='+domain+'">'+(status == 1 ? '⌧' : '⇄︎')+'</a>' +
				'<a href="?opt=delete&domain='+domain+'" class="delete">del</a>' +
				'</div>'+
				'</div>';
		return f;
	}
	proxyapi("domainList",null,function(data){
		var html = "";
		for(var i = 0; i < data.length;i++){
			var domain = data[i];
			html += echoName(domain.domain,domain.open,domain.connectTimes,i);
		}
		$("#proxyDomainList").html(html);
	})
	var analysisDomain = null;
	var analysis = function(){
		var startTime = (new Date())/1000-3600*72;
		startTime -= startTime%3600;
		proxyapi("analysisDataList",{"startTime":startTime,"domain":(analysisDomain?analysisDomain:"")},function(data){
			show(startTime*1000,data.outgoing,data.incoming);
		});
	};
	proxyapi("domainDataList",null,function(data){
		var html = "";
		html += '<div class="dataCount"><span>今日数据流量:</span>'+IntToDataCount(data.countData)+'</div>';
		var list = data.list;
		
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
			analysis();
		});
		showallbutton();
	})
	setInterval(analysis,20000);
	analysis();
})