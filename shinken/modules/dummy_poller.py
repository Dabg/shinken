#!/usr/bin/python
#Copyright (C) 2009 Gabes Jean, naparuba@gmail.com
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


#This Class is an example of an Scheduler module
#Here for the configuration phase AND running one

import sys
import signal
import time
from Queue import Empty


from shinken.basemodule import BaseModule


properties = {
    'daemons' : ['poller'],
    'type' : 'dummy_poller',
    'external' : False,
    'phases' : ['worker'],
}


#called by the plugin manager to get a broker
def get_instance(mod_conf):
    print "Get a Dummy poller module for plugin %s" % mod_conf.get_name()
    instance = Dummy_poller(mod_conf)
    return instance



#Just print some stuff
class Dummy_poller(BaseModule):
    
    def __init__(self, mod_conf):
        BaseModule.__init__(self, mod_conf)


    # Called by poller to say 'let's prepare yourself guy'
    def init(self):
        print "Initilisation of the dummy poller module"
        self.i_am_dying = False



    # Get new checks if less than nb_checks_max
    # If no new checks got and no check in queue,
    # sleep for 1 sec
    # REF: doc/shinken-action-queues.png (3)
    def get_new_checks(self):
        try:
            while(True):
                #print "I", self.id, "wait for a message"
                msg = self.s.get(block=False)
                if msg is not None:
                    self.checks.append(msg.get_data())
                #print "I", self.id, "I've got a message!"
        except Empty , exp:
            if len(self.checks) == 0:
                time.sleep(1)


    # Launch checks that are in status
    # REF: doc/shinken-action-queues.png (4)
    def launch_new_checks(self):
        #queue
        for chk in self.checks:
            if chk.status == 'queue':
                print "Dummy (bad) check for", chk.command
                chk.exit_status = 2
                chk.get_outputs('All is NOT SO well', 8012)
                chk.status = 'done'
                chk.execution_time = 0.1



    # Check the status of checks
    # if done, return message finished :)
    # REF: doc/shinken-action-queues.png (5)
    def manage_finished_checks(self):
        to_del = []
        for action in self.checks:
            to_del.append(action)
            try:
                self.returns_queue.append(action)
            except IOError , exp:
                print "[%d]Exiting: %s" % (self.id, exp)
                sys.exit(2)
        for chk in to_del:
            self.checks.remove(chk)


    #id = id of the worker
    #s = Global Queue Master->Slave
    #m = Queue Slave->Master
    #return_queue = queue managed by manager
    #c = Control Queue for the worker
    def work(self, s, returns_queue, c):
        print "Module Dummy started!"
        ## restore default signal handler for the workers:
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        timeout = 1.0
        self.checks = []
        self.returns_queue = returns_queue
        self.s = s
        self.t_each_loop = time.time()
        while True:
            begin = time.time()
            msg = None
            cmsg = None

            # If we are diyin (big problem!) we do not
            # take new jobs, we just finished the current one
            if not self.i_am_dying:
                # REF: doc/shinken-action-queues.png (3)
                self.get_new_checks()
                # REF: doc/shinken-action-queues.png (4)
                self.launch_new_checks()
            # REF: doc/shinken-action-queues.png (5)
            self.manage_finished_checks()

            # Now get order from master
            try:
                cmsg = c.get(block=False)
                if cmsg.get_type() == 'Die':
                    print "[%d]Dad say we are diing..." % self.id
                    break
            except :
                pass

            timeout -= time.time() - begin
            if timeout < 0:
                timeout = 1.0


