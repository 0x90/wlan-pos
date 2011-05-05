#!/bin/bash

VENV_HOME=/opt/wpp
WPP_HOME=$VENV_HOME/src/wlan-pos

cd $WPP_HOME
. $VENV_HOME/bin/activate

timestamp=`date +%Y-%m%d`
python offline.py -u 1 >> $WPP_HOME/log/upalgodb_$timestamp.log 2>&1
