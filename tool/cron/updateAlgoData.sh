#!/bin/bash

VENV_HOME=/opt/wpp
WPP_HOME=$VENV_HOME/src/wlan-pos

cd $WPP_HOME
. $VENV_HOME/bin/activate

datetime=`date +%Y-%m%d`
timestamp=`date +%Y-%m%d-%H%M%S`
thisfilename=`basename $0 |awk -F. '{print $1}'`
task_banner="\n========= TASK:$thisfilename WAKEUP@$timestamp ========"
echo -e $task_banner  >> $WPP_HOME/log/upalgodb_$datetime.log 2>&1
python offline.py -u 1 >> $WPP_HOME/log/upalgodb_$datetime.log 2>&1
