<h2>DDDProxy</h2>
私有安全的代理软件，翻墙用的，用Python写的 - by dx.wang

E-Mail：wdongxv@gmail.com


<h3>主要有以下功能或特点</h3>
*	私有的代理软件
*	自动把被墙的网站走梯子（原理见：https://en.wikipedia.org/wiki/Proxy_auto-config ）
*	会自动读取gfwlist，就是说基本上被墙的网站会自动加到翻墙列表里去
*	对每个域名下的网站访问次数的统计
*	在一定时间内，每个客户端每小时分别访问哪些网站所用流量的统计
*	pac列表会以统计为标准，将访问次数较多的网站放到最前面来减少客户端的运算
*	远程服务器与本地服务器之间采用SSL加密

<h3>如何运行？</h3>
在远程服务器(当然就是境外服务器了)运行: 
<pre>python remoteServer.py [passWord]</pre>
本地服务器运行: 
<pre>python localServer.py [remoteServerHost] [passWord]</pre>
假装你也在ip为192.168.2.4搭建了local server，然后用你要翻墙的机器上用浏览器打开：
<pre>http://192.168.2.4:8081/</pre>
这样你就会看到完整的帮助了

<h3>下面是DDDProxy的管理界面截图：</h3>
<img src="http://i.imgur.com/GJcVlb8.png"/>
<img src="http://i.imgur.com/SsgX2z4.png"/>

<h3>当然，做为新的开源项目，还有很多事要做的：</h3>
*	多服务器支持
*	pac文件还没有做缓存
*	tornado框架需要去掉或改为傻瓜式安装
*	现在作者是用supervisor来做开机启动，当然也是需要傻瓜一键安装无烦恼自启动功能的




<h2>以下是2015年04月18日之前装逼的时候写的</h2>

DDDProxy

a private security HTTP/HTTPS proxy framework,with python

* Private
* Auto proxy(see https://en.wikipedia.org/wiki/Proxy_auto-config)
* Security Proxy
* Anti-GFW
* No need install certificate on user browser
* Fast

2015年4月15号
	*新增 自动读取加载gfwlist #https://autoproxy-gfwlist.googlecode.com/svn/trunk/gfwlist.txt
	*http1.0可能会有点问题，已经修复


* proxy service can run on:
	Linux,Unix,Windows

* proxy service support devices/system:
	1.windows xp+
	2.iPhone,iPad
	3.Android 5.0+
	4.Mac OS X
	5.other support PAC auto proxy
* How to install
	windows
	

* How To run
	1. remote server run : python remoteServer.py [passWord]
	2. local server run: python localServer.py [remoteServerHost] [passWord]
	3. then open http://localip:8081,see help


