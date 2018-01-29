<h2>DDDProxy 3.2.3</h2>
私有安全的代理软件
<h3>主要有以下功能或特点</h3>

*	增加一键安装功能 支持 MacOs，Centos 7+，Ubuntu
*	增加对SOCKS5代理协议的兼容（3.2.0版本新增）
*	异步I/O
*	多远程服务器支持(2015年8月8日新增)
*	私有的代理软件
*	自动代理配置（原理见：https://en.wikipedia.org/wiki/Proxy_auto-config ）
*	对每个域名下的网站访问次数的统计
*	在一定时间内，每个客户端每小时分别访问哪些网站所用流量的统计
*	pac列表会以统计为标准，将访问次数较多的网站放到最前面来减少客户端的运算
*	远程服务器与本地服务器之间采用SSL加密
*	代理域名列表可备份到Google Drive

<h3>安装向导</h3>
在远程服务器运行: 
<pre>python install.py remoteServer</pre>
本地服务器运行: 
<pre>python install.py localServer</pre>
