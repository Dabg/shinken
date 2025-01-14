#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

#
# This file is used to test reading and processing of config files
#

#It's ugly I know....
from shinken_test import *
from worker import Worker
from multiprocessing import Queue, Manager
from objects.service import Service
from objects.contact import Contact
modconf = Module()

class TestTimeout(ShinkenTest):
    #Uncomment this is you want to use a specific configuration
    #foreyour test
    def setUp(self):
        self.setup_with_file('etc/nagios_check_timeout.cfg')

    
    def test_notification_timeout(self):
        if os.name == 'nt':
            return

        # These queues connect a poller/reactionner with a worker
        to_queue = Queue()
        manager = Manager()
        from_queue = manager.list()
        control_queue = Queue()


        # This testscript plays the role of the reactionner
        # Now "fork" a worker
        w = Worker(1,to_queue,from_queue,1)
        w.id = 1
        w.i_am_dying = False

        # We prepare a notification in the to_queue
        c = Contact()
        c.contact_name = "mr.schinken"
        n = Notification('PROBLEM', 'scheduled', 'libexec/sleep_command.sh 7', '', Service(), '', '', id=1)
        n.status = "queue"
        #n.command = "libexec/sleep_command.sh 7"
        n.t_to_go = time.time()
        n.contact = c
        n.timeout = 2
        n.env = {}
        n.exit_status = 0
        n.module_type = "fork"
        nn = n.copy_shell()

        # Send the job to the worker
        msg = Message(id=0, type='Do', data=nn)
        to_queue.put(msg)

        w.checks = []
        w.returns_queue = from_queue
        w.s = to_queue
        w.c = control_queue
        # Now we simulate the Worker's work() routine. We can't call it
        # as w.work() because it is an endless loop
        for i in xrange(1,10):
            w.get_new_checks()
            # During the first loop the sleeping command is launched
            w.launch_new_checks()
            w.manage_finished_checks()
            time.sleep(1)

        # The worker should have finished it's job now, either correctly or
        # with a timeout
        o = from_queue.pop()

        self.assert_(o.status == 'timeout')
        self.assert_(o.exit_status == 3)
        self.assert_(o.execution_time < n.timeout+1)

        # Be a good poller and clean up.
        to_queue.close()
        control_queue.close()

        # Now look what the scheduler says to all this
        self.sched.actions[n.id] = n
        self.sched.put_results(o)
        self.assert_(self.any_log_match("Warning: Contact mr.schinken service notification command 'libexec/sleep_command.sh 7 ' timed out after 2 seconds"))


if __name__ == '__main__':
    unittest.main()

