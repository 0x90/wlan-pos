#!/bin/bash

HOME=/home/YanXT
#VENV_HOME=/opt/wpp
VENV_HOME=$HOME/envs/wpp_py26
#WPP_HOME=$VENV_HOME/src/wpp
WPP_HOME=$HOME/wpp
LOGDIR=$HOME/tmp/log/cron
PYDIR=$WPP_HOME/wpp/util

. $VENV_HOME/bin/activate

datetime=`date +%Y-%m%d`
timestamp=`date +%Y-%m%d-%H%M%S`
thisfilename=`basename $0 |awk -F. '{print $1}'`
logfile=reserveCourse_$datetime.log

task_banner="\n========= TASK:$thisfilename WAKEUP@$timestamp ========"
[ -d $LOGDIR ] || mkdir -p $LOGDIR
echo -e $task_banner  >> $LOGDIR/$logfile 2>&1

export PYTHONPATH=$WPP_HOME
cd $PYDIR
python yc.py >> $LOGDIR/$logfile 2>&1
