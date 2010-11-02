#!/bin/bash
#Copyright (C) 2009-2010 :
#    Gabes Jean, naparuba@gmail.com
#    Gerhard Lausser, Gerhard.Lausser@consol.de
#
#This file is part of Shinken.
#
#Shinken is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Shinken is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Affero General Public License for more details.
#
#You should have received a copy of the GNU Affero General Public License
#along with Shinken.  If not, see <http://www.gnu.org/licenses/>.


#set -x

echo "Begining test END TO END"


DIR=$(cd $(dirname "$0"); pwd)
echo "Going to dir $DIR/.."
cd $DIR/..





#check for a process existance with good number
function check_process_nb {
    NB=`ps -fu shinken | grep python | grep -v grep | grep $1 | wc -l`
    if [ $NB != "$2" ]
    then
	echo "Error : There is not enouth $1 launched (only $NB)."
	exit 2
    else
	echo "Ok, got $NB $1"
    fi
}

function is_file_present {
    if [ -f $1 ]
    then
	echo "File $1 is present."
    else
	echo "Error : File $1 is missing!"
	exit 2
    fi
}

function string_in_file {
    grep "$1" $2
    if [ $? != 0 ]
    then
	echo "Error : the file $2 is missing string $1 !"
	exit 2
    else
	echo "The string $1 is in $2"
    fi
}


function check_good_run {
    VAR="$1"
    echo "Check for $NB_SCHEDULERS Scheduler"
    check_process_nb scheduler $NB_SCHEDULERS
    is_file_present $VAR/schedulerd.pid

    echo "Check for $NB_POLLERS pollers (1 master, 1 for multiporcess module (queue manager), 4 workers)"
    check_process_nb poller $NB_POLLERS
    is_file_present $VAR/pollerd.pid

    echo "Check for $NB_REACTIONNERS reactionners (1 master, 1 for multiporcess module (queue manager) 1 worker)"
    check_process_nb reactionner $NB_REACTIONNERS
    is_file_present $VAR/reactionnerd.pid

    echo "Check for $NB_BROKERS brokers (one master, one for status.dat, one for log)"
    check_process_nb broker $NB_BROKERS
    is_file_present $VAR/brokerd.pid

    echo "Check for $NB_ARBITERS arbiter"
    check_process_nb arbiter $NB_ARBITERS
    is_file_present $VAR/arbiterd.pid

    echo "Now checking for good file prensence"
    ls var
    is_file_present $VAR/nagios.log
    string_in_file "Waiting for initial configuration" $VAR/nagios.log
    string_in_file "First scheduling" $VAR/nagios.log
    string_in_file "OK, all schedulers configurations are dispatched :)" $VAR/nagios.log
    string_in_file "OK, no more reactionner sent need" $VAR/nagios.log
    string_in_file "OK, no more poller sent need" $VAR/nagios.log
    string_in_file "OK, no more broker sent need" $VAR/nagios.log
}


#Standard launch process packets
NB_SCHEDULERS=1
NB_POLLERS=6
NB_REACTIONNERS=3
NB_BROKERS=3
NB_ARBITERS=1



echo "Clean old tests and kill remaining processes"
./clean.sh


echo "####################################################################################"
echo "#                                                                                  #"
echo "#                           SIMPLE START                                           #"
echo "#                                                                                  #"
echo "####################################################################################"

echo "Now we can start some launch tests"
bin/launch_all_debug.sh


echo "Now checking for existing apps"

echo "we can sleep 5sec for conf dispatching and so good number of process"
sleep 5

#Now check if the run looks good with var in the direct directory
check_good_run var

echo "First launch check OK"

echo "Now we clean it and test an install"
./clean.sh

echo "####################################################################################"
echo "#                                                                                  #"
echo "#                           DUMMY INSTALL                                          #"
echo "#                                                                                  #"
echo "####################################################################################"

echo "Now installing the application in DUMMY mode"
python setup.py install --root=/tmp/moncul --record=INSTALLED_FILES --install-scripts=/usr/bin

if [ $? != '0' ]
then
    echo "Error : the dummy install failed."
    exit 2
fi
echo "Dummy install OK"

echo "I reclean all for a real install"
./clean.sh

echo "####################################################################################"
echo "#                                                                                  #"
echo "#                           REAL INSTALL                                           #"
echo "#                                                                                  #"
echo "####################################################################################"

echo "Now a REAL install"
sudo python setup.py install --install-scripts=/usr/bin
if [ $? != '0' ]
then
    echo "Error : the real install failed."
    exit 2
fi
echo "Real install OK"

#Useful to take it from setup_parameter? It's just for coding here
ETC=/etc/shinken
is_file_present $ETC/nagios.cfg
is_file_present $ETC/shinken-specific.cfg
string_in_file "servicegroups.cfg" $ETC/nagios.cfg
is_file_present /usr/bin/shinken-arbiter

echo "Now we can test a real run guy"
/etc/init.d/shinken-scheduler start
/etc/init.d/shinken-poller start
/etc/init.d/shinken-reactionner start
/etc/init.d/shinken-broker start
/etc/init.d/shinken-arbiter start

echo "We will sleep again 5sec so every one is quite stable...."
sleep 5
check_good_run /var/lib/shinken

echo "OK Great. Even the real launch test pass. Great. I can clean after me."
./clean.sh




echo "####################################################################################"
echo "#                                                                                  #"
echo "#                                    HA launch                                     #"
echo "#                                                                                  #"
echo "####################################################################################"

echo "Now we can start some launch tests"
bin/launch_all_debug2.sh


echo "Now checking for existing apps"

echo "we can sleep 5sec for conf dispatching and so good number of process"
sleep 5

#The number of process changed, we mush look for it


#Standard launch process packets
NB_SCHEDULERS=2
#6 for stack 1, and 2 for 2 (not active, so no worker)
NB_POLLERS=8
#3 for stack1, 2 for stack2 (no worker from now)
NB_REACTIONNERS=5
#3 for stack 1, 1 for stack2 (no status.dat nor log worker launch)
NB_BROKERS=4
#still 1
NB_ARBITERS=1

#Now check if the run looks good with var in the direct directory
check_good_run var

echo "All launch of HA daemons is OK"

#Now we kill and see if all is OK :)
#We clean the log file
#$VAR/nagios.log

#We kill the most important thing first : the scheduler-Master
bin/stop_scheduler.sh

#We sleep to be sruethe scheduler see us
sleep 5
NB_SCHEDULERS=1
#string_in_file "Warning : Scheduler scheduler-Master had the configuration 0 but is dead, I am not happy." $VAR/nagios.log

#check_good_run var


echo "Now we clean it and test an install"
./clean.sh



echo "All check are OK. Congrats! You can go take a Beer ;)"
