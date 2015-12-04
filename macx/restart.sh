#!/bin/bash
plistPath=~/Library/LaunchAgents/com.wangdongxu.ddproxy.plist
echo "Stop ..."
launchctl unload $plistPath
echo "Starting ..."
launchctl load $plistPath
echo "Done"
