#!/bin/bash
#'''
#Created on 2016年7月7日
#
#@author: zhujin
#'''

TS=$(date "+%Y%m%d%H%M")
filepath=$(cd "$(dirname "$0")"; pwd);cd ${filepath}/../logs/

mkdir metrics_logs
cp -f *.log metrics_logs
tar -czf metrics_logs.${TS}.tar.gz metrics_logs
rm -rf metrics_logs

for log in `ls *.log`
do
>${log}
done
