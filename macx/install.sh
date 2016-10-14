#!/bin/bash
echo "Install ..."
current="$(dirname ${0})";
cd $current
rootDir=$(dirname $(pwd))

plistPath=~/Library/LaunchAgents/com.wangdongxu.ddproxy.plist
plist=$(cat "$(pwd)/com.wangdongxu.ddproxy.plist")
plist=${plist/path-to-DDDProxy/$rootDir}

if [ ! -d ~/Library/LaunchAgents ]; then
	echo "mkdir ~/Library/LaunchAgents"
	mkdir ~/Library/LaunchAgents
fi


echo "Install $plistPath ..."
echo $plist > $plistPath

echo "Starting ..."
launchctl load $plistPath
sleep 1
url="http://127.0.0.1:8080"
echo "open $url"
open $url

echo "Started !"
