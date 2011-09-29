#!/bin/bash

#HOME=/home/alexy #x200
#WPP_HOME=$HOME/wpp #R61,x200
#VENV_HOME=$HOME/envs/wpp_py26 #R61
VENV_HOME=/opt/wpp #vm
#HOME=/home/YanXT #R61

WPP_HOME=$VENV_HOME/src/wpp #vm

LOGDIR=$HOME/tmp/log/yc
PYDIR=$WPP_HOME/wpp/util

. $VENV_HOME/bin/activate #vm

datetime=`date +%Y-%m%d`
timestamp=`date +%Y-%m%d-%H%M%S`
thisfilename=`basename $0 |awk -F. '{print $1}'`
logfile=yc.log
log=$LOGDIR/$logfile

task_banner="\n========= TASK:$thisfilename WAKEUP@$timestamp ========"
[ -d $LOGDIR ] || mkdir -p $LOGDIR
echo -e $task_banner  >> $log 2>&1

export PYTHONPATH=$WPP_HOME:$PYTHONPATH
cd $PYDIR
python yc.py >> /dev/null 2>&1
