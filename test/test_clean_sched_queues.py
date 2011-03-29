#!/usr/bin/env python2.6
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


class TestSchedCleanQueues(ShinkenTest):
    #Uncomment this is you want to use a specific configuration
    #for your test
    def setUp(self):
        self.setup_with_file('etc/nagios_clean_sched_queues.cfg')

    
    # Try to generate a bunch of external commands
    # and see if they are drop like it should
    def test_sched_clean_queues(self):
        print "Get the hosts and services"
        now = time.time()
        host = self.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = [] # ignore the router
        router = self.sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = [] # ignore the router
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        print "Len actions", host.actions
        #host.__class__.obsess_over = True
        #host.obsess_over_host = True
        for i in xrange(1, 1001):
            host.get_obsessive_compulsive_processor_command()
        print "New len", len(host.actions)
        self.assert_(len(host.actions) >= 1000)
        self.sched.get_new_actions()
        print len(self.sched.actions)
        # So get our 1000 external commands
        self.assert_(len(self.sched.actions) >= 1000)
        
        # Try to call the clean ,they are jsut too many!
        self.sched.clean_queues()
        # Should have something like 16 event handler
        print len(self.sched.actions)
        self.assert_(len(self.sched.actions) < 30)

        #Now for Notifications and co
        host.notification_interval = 0.000001
        for i in xrange(1, 1001):
            host.create_notifications('PROBLEM')
        self.sched.get_new_actions()
        print len(self.sched.actions)
        # So get our 1000 notifications
        self.assert_(len(self.sched.actions) >= 1000)

        # Try to call the clean ,they are jsut too many!
        self.sched.clean_queues()
        print len(self.sched.actions)
        self.assert_(len(self.sched.actions) < 30)


if __name__ == '__main__':
    unittest.main()

