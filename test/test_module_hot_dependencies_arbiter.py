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

import os, sys, time

from shinken_test import unittest, ShinkenTest

from shinken.log import logger

from shinken.objects.module import Module

from shinken.modules import hot_dependencies_arbiter
from shinken.modules.hot_dependencies_arbiter import Hot_dependencies_arbiter, get_instance


modconf = Module()
modconf.module_name = "PickleRetention"
modconf.module_type = hot_dependencies_arbiter.properties['type']
modconf.properties = hot_dependencies_arbiter.properties.copy()


try:
    import json
except ImportError: 
    # For old Python version, load 
    # simple json (it can be hard json?! It's 2 functions guy!)
    try:
        import simplejson as json
    except ImportError:
        print "Error : you need the json or simplejson module for this script"
        sys.exit(0)

class TestModuleHotDep(ShinkenTest):
    #setUp is in shinken_test
    def setUp(self):
        self.setup_with_file('etc/nagios_module_hot_dependencies_arbiter.cfg')

    #Change ME :)
    def test_simple_json_read(self):
        print self.conf.modules

        host0 = self.sched.conf.hosts.find_by_name('test_host_0')
        self.assert_(host0 is not None)
        host1 = self.sched.conf.hosts.find_by_name('test_host_1')
        self.assert_(host1 is not None)
        host2 = self.sched.conf.hosts.find_by_name('test_host_2')
        self.assert_(host2 is not None)

        # From now there is no link between hosts (just parent with the router)
        # but it's not imporant here
        self.assert_(host0.is_linked_with_host(host1) == False)
        self.assert_(host1.is_linked_with_host(host0) == False)
        self.assert_(host0.is_linked_with_host(host2) == False)
        self.assert_(host2.is_linked_with_host(host0) == False)
        self.assert_(host2.is_linked_with_host(host1) == False)
        self.assert_(host1.is_linked_with_host(host2) == False)

    
        #get our modules
        mod = sl = Hot_dependencies_arbiter(modconf, 'tmp/vmware_mapping_file.json', "", 30, 300)
        
        try :
            os.unlink(mod.mapping_file)
        except :
            pass
        
        print "Instance", sl

        # Hack here :(
        sl.properties = {}
        sl.properties['to_queue'] = None
        sl.init()
        l = logger

        # We simulate a uniq link, here the vm host1 is on the host host0
        links = [[["host", "test_host_0"], ["host", "test_host_1"]]]
        f = open(mod.mapping_file, 'wb')
        f.write(json.dumps(links))
        f.close()

        # Try the hook for the late config, so it will create
        # the link between host1 and host0
        sl.hook_late_configuration(self)

        # We can look is now the hosts are linked or not :)
        self.assert_(host1.is_linked_with_host(host0) == True)

        print "Mapping after first pass?", sl.mapping

        # We sleep because the dile we generated should have
        # a different modification time, so more than 1s
        time.sleep(1.5)

        ### Ok now we update the mappign file with this time
        # link between 1 and 2, bye bye 0 :)
        # host2 is the host, host1 the VM
        links = [[["host", "test_host_2"], ["host", "test_host_1"]]]
        f = open(mod.mapping_file, 'wb')
        f.write(json.dumps(links))
        f.close()
        
        sl.hook_tick(self)
        
        # Now we should see link between 1 and 2, but not between 0 and 1
        self.assert_(host1.is_linked_with_host(host0) == False)
        self.assert_(host1.is_linked_with_host(host2) == True)

        #Ok, we can delete the retention file
        os.unlink(mod.mapping_file)




    # We are trying to see if we can have good data with 2 commands call
    # CASE1 : link between host0 and 1
    # then after some second, :
    # CASE2 : link between host1 and host2, so like the previous test, but with
    # command calls
    def test_json_read_with_command(self):
        print self.conf.modules

        host0 = self.sched.conf.hosts.find_by_name('test_host_0')
        self.assert_(host0 is not None)
        host1 = self.sched.conf.hosts.find_by_name('test_host_1')
        self.assert_(host1 is not None)
        host2 = self.sched.conf.hosts.find_by_name('test_host_2')
        self.assert_(host2 is not None)

        # From now there is no link between hosts (just parent with the router)
        # but it's not imporant here
        self.assert_(host0.is_linked_with_host(host1) == False)
        self.assert_(host1.is_linked_with_host(host0) == False)
        self.assert_(host0.is_linked_with_host(host2) == False)
        self.assert_(host2.is_linked_with_host(host0) == False)
        self.assert_(host2.is_linked_with_host(host1) == False)
        self.assert_(host1.is_linked_with_host(host2) == False)

    
        #get our modules
        mod = None
        mod = Module({'type' : 'hot_dependencies', 'module_name' : 'VMWare_auto_linking', 'mapping_file' : 'tmp/vmware_mapping_file.json',
                      'mapping_command' : "libexec/hot_dep_export.py case1 tmp/vmware_mapping_file.json", 'mapping_command_interval' : '30'})
        
        try :
            os.unlink(mod.mapping_file)
        except :
            pass
        
        sl = get_instance(mod)
        print "Instance", sl
        
        # Hack here :(
        sl.properties = {}
        sl.properties['to_queue'] = None
        sl.init()
        l = logger

        # Try the hook for the late config, so it will create
        # the link between host1 and host0
        sl.hook_late_configuration(self)

        # We can look is now the hosts are linked or not :)
        self.assert_(host1.is_linked_with_host(host0) == False)
        
        print "Mapping after first pass?", sl.mapping

        # The hook_late should have seen a problem of no file
        # and so launch the command. We can wait it finished
        time.sleep(1.5)

        # Now we look if it's finished, and we get data and manage them
        # with case 1 (0 and 1 linked, not with 1 and 2)
        sl.hook_tick(self)
        
        # Now we should see link between 1 and 0, but not between 2 and 1
        self.assert_(host1.is_linked_with_host(host0) == True)
        self.assert_(host1.is_linked_with_host(host2) == False)

        # Now we go in case2
        print "Go in case2 " * 10
        if os.name != 'nt':
            sl.mapping_command = 'libexec/hot_dep_export.py case2 tmp/vmware_mapping_file.json'
        else:
            sl.mapping_command = 'libexec\\hot_dep_export.py case2 tmp\\vmware_mapping_file.json'
        # We lie in the interval :p (not 0, because 0 mean : disabled)
        sl.mapping_command_interval = 0.1
        sl.hook_tick(self)
        time.sleep(1.5)
        #But we need another tick to get all of it
        sl.hook_tick(self)

        # Now we should see link between 1 and 0, but not between 2 and 1
        self.assert_(host1.is_linked_with_host(host0) == False)
        self.assert_(host1.is_linked_with_host(host2) == True)


        #Ok, we can delete the retention file
        os.unlink(mod.mapping_file)




if __name__ == '__main__':
    unittest.main()

