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


class TestConfig(ShinkenTest):
    def setUp(self):
        # i am arbiter-like
        Config.fill_usern_macros()
        self.broks = {}
        self.me = None
        self.log = Log()
        self.log.load_obj(self)
        self.config_files = ['etc/nagios_resultmodulation.cfg']
        self.conf = Config()
        self.conf.read_config(self.config_files)
        self.conf.instance_id = 0
        self.conf.instance_name = 'test'
        self.conf.linkify_templates()
        self.conf.apply_inheritance()
        self.conf.explode()
        self.conf.create_reversed_list()
        self.conf.remove_twins()
        self.conf.apply_implicit_inheritance()
        self.conf.fill_default()
        self.conf.clean_useless()
        self.conf.pythonize()
        self.conf.linkify()
        self.conf.apply_dependancies()
        self.conf.explode_global_conf()
        self.conf.is_correct()
        self.confs = self.conf.cut_into_parts()
        self.dispatcher = Dispatcher(self.conf, self.me)
        self.sched = Scheduler(None)
        m = MacroResolver()
        m.init(self.conf)
        self.sched.load_conf(self.conf)
        e = ExternalCommand(self.conf, 'applyer')
        self.sched.external_command = e
        e.load_scheduler(self.sched)
        self.sched.schedule()


    def get_svc(self):
        return self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")

    def get_host(self):
        return self.sched.hosts.find_by_name("test_host_0")
    

    def get_router(self):
        return self.sched.hosts.find_by_name("test_router_0")

    #Change ME :)
    def test_service_resultmodulation(self):
        svc = self.get_svc()
        host = self.get_host()
        router = self.get_router()
        
        self.scheduler_loop(2, [[host, 0, 'UP | value1=1 value2=2'], [svc, 2, 'BAD | value1=0 value2=0'], ])
        self.assert_(host.state == 'UP')
        self.assert_(host.state_type == 'HARD')
        
        #This service got a result modulation. So Criticals are in fact
        #Warnings. So even with some CRITICAL (2), it must be warning
        self.assert_(svc.state == 'WARNING')

        #If we remove the resultmodulations, we should have theclassic behavior
        svc.resultmodulations = []
        self.scheduler_loop(2, [[host, 0, 'UP | value1=1 value2=2'], [svc, 2, 'BAD | value1=0 value2=0']])
        self.assert_(svc.state == 'CRITICAL')

        #Now look for the inheritaed thing
        #resultmodulation is a inplicit inherited parameter
        #and router define it, but not test_router_0/test_ok_0. So this service should also be impacted
        svc2 = self.sched.services.find_srv_by_name_and_hostname("test_router_0", "test_ok_0")
        self.assert_(svc2.resultmodulations == router.resultmodulations)
        
        self.scheduler_loop(2, [[svc2, 2, 'BAD | value1=0 value2=0']])
        self.assert_(svc2.state == 'WARNING')
        

if __name__ == '__main__':
    unittest.main()

