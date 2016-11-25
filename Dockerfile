FROM centos:7
MAINTAINER dxw<wdongxv@gmail.com>
COPY . /
#docker run -d -p 0.0.0.0:8088:8088 --restart=always dddproxy python localServer.py -p 8088
