#!/usr/bin/env python2.6
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
# This file is used to test host- and service-downtimes.
#

from shinken_test import *
import os
import re
import subprocess
import shutil
import time
import random
import copy

from shinken.brok import Brok
from shinken.objects.timeperiod import Timeperiod
from shinken.objects.module import Module
from shinken.comment import Comment

from shinken.modules import livestatus_broker
from shinken.modules.livestatus_broker import Livestatus_broker

sys.setcheckinterval(10000)

modconf = Module()
modconf.module_name = "livestatus"
modconf.module_type = livestatus_broker.properties['type']
modconf.properties = livestatus_broker.properties.copy()

class TestConfig(ShinkenTest):
    def contains_line(self, text, pattern):
        regex = re.compile(pattern)
        for line in text.splitlines():
            if re.search(regex, line):
                return True
        return False


    def scheduler_loop(self, count, reflist, do_sleep=False, sleep_time=61):
        super(TestConfig, self).scheduler_loop(count, reflist, do_sleep, sleep_time)
        if self.nagios_installed() and hasattr(self, 'nagios_started'):
            self.nagios_loop(1, reflist)
  

    def update_broker(self, dodeepcopy=False):
        #The brok should be manage in the good order
        ids = self.sched.broks.keys()
        ids.sort()
        for brok_id in ids:
            brok = self.sched.broks[brok_id]
            #print "Managing a brok type", brok.type, "of id", brok_id
            #if brok.type == 'update_service_status':
            #    print "Problem?", brok.data['is_problem']
            if dodeepcopy:
                brok = copy.deepcopy(brok)
            self.livestatus_broker.manage_brok(brok)
        self.sched.broks = {}


    def lines_equal(self, text1, text2):
        # gets two multiline strings and compares the contents
        # lifestatus output may not be in alphabetical order, so this
        # function is used to compare unordered output with unordered
        # expected output
        # sometimes mklivestatus returns 0 or 1 on an empty result
        text1 = text1.replace("200           1", "200           0")
        text2 = text2.replace("200           1", "200           0")
        text1 = text1.rstrip()
        text2 = text2.rstrip()
        #print "text1 //%s//" % text1
        #print "text2 //%s//" % text2
        sorted1 = "\n".join(sorted(text1.split("\n")))
        sorted2 = "\n".join(sorted(text2.split("\n")))
        len1 = len(text1.split("\n"))
        len2 = len(text2.split("\n"))
        #print "%s == %s text cmp %s" % (len1, len2, sorted1 == sorted2)
        #print "text1 //%s//" % sorted(text1.split("\n"))
        #print "text2 //%s//" % sorted(text2.split("\n"))
        if sorted1 == sorted2 and len1 == len2:
            return True
        else:
            # Maybe list members are different
            # allhosts;test_host_0;test_ok_0;servicegroup_02,servicegroup_01,ok
            # allhosts;test_host_0;test_ok_0;servicegroup_02,ok,servicegroup_01
            # break it up to
            # [['allhosts'], ['test_host_0'], ['test_ok_0'],
            #     ['ok', 'servicegroup_01', 'servicegroup_02']]
            [line for line in sorted(text1.split("\n"))]
            data1 = [[sorted(c.split(',')) for c in columns] for columns in [line.split(';') for line in sorted(text1.split("\n")) if line]]
            data2 = [[sorted(c.split(',')) for c in columns] for columns in [line.split(';') for line in sorted(text2.split("\n")) if line]]
            #print "text1 //%s//" % data1
            #print "text2 //%s//" % data2
            # cmp is clever enough to handle nested arrays 
            return cmp(data1, data2) == 0
            

    def show_broks(self, title):
        print
        print "--- ", title
        for brok in sorted(self.sched.broks.values(), lambda x, y: x.id - y.id):
            if re.compile('^service_').match(brok.type):
                print "BROK:", brok.type
                print "BROK   ", brok.data['in_checking']
        self.update_broker()
        request = 'GET services\nColumns: service_description is_executing\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response


    def nagios_installed(self, path='/usr/local/nagios/bin/nagios', livestatus='/usr/local/nagios/lib/mk-livestatus/livestatus.o'):
        return False
        raise
        if os.path.exists(path) and os.access(path, os.X_OK) and os.path.exists(livestatus):
            self.nagios_path = path
            self.livestatus_path = livestatus
            return True
        else:
            return False


    # shinkenize_nagios_config('nagios_1r_1h_1s')
    # We assume that there is a nagios_1r_1h_1s.cfg and a nagios_1r_1h_1s directory for the objects
    def unshinkenize_config(self, configname):
        new_configname = configname + '_' + str(os.getpid())
        config = open('etc/nagios_' + configname + '.cfg')
        text = config.readlines()
        config.close()

        newconfig = open('etc/nagios_' + new_configname + '.cfg', 'w')
        for line in text:
            if re.search('^resource_file=', line):
                newconfig.write("resource_file=etc/resource.cfg\n")
            elif re.search('shinken\-specific\.cfg', line):
                pass
            elif re.search('enable_problem_impacts_states_change', line):
                pass
            elif re.search('cfg_dir=', line):
                newconfig.write(re.sub(configname, new_configname, line))
            elif re.search('cfg_file=', line):
                newconfig.write(re.sub(configname, new_configname, line))
            elif re.search('execute_host_checks=', line):
                newconfig.write("execute_host_checks=0\n")
            elif re.search('execute_service_checks=', line):
                newconfig.write("execute_service_checks=0\n")
            elif re.search('^debug_level=', line):
                newconfig.write("debug_level=0\n")
            elif re.search('^debug_verbosity=', line):
                newconfig.write("debug_verbosity=0\n")
            elif re.search('^status_update_interval=', line):
                newconfig.write("status_update_interval=30\n")
            elif re.search('^command_file=', line):
                newconfig.write("command_file=var/nagios.cmd\n")
            elif re.search('^command_check_interval=', line):
                newconfig.write("command_check_interval=1s\n")
            else:
                newconfig.write(line)
        newconfig.write('broker_module=/usr/local/nagios/lib/mk-livestatus/livestatus.o var/live' + "\n")
        newconfig.close()
        for dirfile in os.walk('etc/' + configname):
            dirpath, dirlist, filelist = dirfile
            newdirpath = re.sub(configname, new_configname, dirpath)
            os.mkdir(newdirpath)
            for file in [f for f in filelist if re.search('\.cfg$', f)]:
                config = open(dirpath + '/' + file)
                text = config.readlines()
                config.close()
                newconfig = open(newdirpath + '/' + file, 'w')
                for line in text:
                    if re.search('^\s*criticity', line):
                        pass
                    elif re.search('enable_problem_impacts_states_change', line):
                        pass
                    else:
                        newconfig.write(line)
                newconfig.close()
        return new_configname

    
    def start_nagios(self, config):
        if os.path.exists('var/spool/checkresults'):
            # Cleanup leftover checkresults
            shutil.rmtree('var/spool/checkresults')
        for dir in ['tmp', 'var/tmp', 'var/spool', 'var/spool/checkresults', 'var/archives']:
            if not os.path.exists(dir):
                os.mkdir(dir)
        self.nagios_config = self.unshinkenize_config(config)
        if os.path.exists('var/nagios.log'):
            os.remove('var/nagios.log')
        if os.path.exists('var/retention.dat'):
            os.remove('var/retention.dat')
        if os.path.exists('var/status.dat'):
            os.remove('var/status.dat')
        self.nagios_proc = subprocess.Popen([self.nagios_path, 'etc/nagios_' + self.nagios_config + '.cfg'], close_fds=True)
        self.nagios_started = time.time()
        time.sleep(2)


    def stop_nagios(self):
        if self.nagios_installed():
            print "i stop nagios!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            time.sleep(5)
            if hasattr(self, 'nagios_proc'):
                attempt = 1
                while self.nagios_proc.poll() is None and attempt < 4:
                    self.nagios_proc.terminate()
                    attempt += 1
                    time.sleep(1)
                if self.nagios_proc.poll() is None:
                    self.nagios_proc.kill()
                if os.path.exists('etc/' + self.nagios_config):
                    shutil.rmtree('etc/' + self.nagios_config)
                if os.path.exists('etc/nagios_' + self.nagios_config + '.cfg'):
                    os.remove('etc/nagios_' + self.nagios_config + '.cfg')


    def ask_nagios(self, request):
        if time.time() - self.nagios_started < 2:
            time.sleep(1)
        if not request.endswith("\n"):
            request = request + "\n"
        unixcat = subprocess.Popen([os.path.dirname(self.nagios_path) + '/' + 'unixcat', 'var/live'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tic = time.clock()
        out, err = unixcat.communicate(request)
        tac = time.clock()
        print "mklivestatus duration %f" % (tac - tic)
        attempt = 1
        while unixcat.poll() is None and attempt < 4:
            unixcat.terminate()
            attempt += 1
            time.sleep(1)
        if unixcat.poll() is None:
            unixcat.kill()
        print "unixcat says", out
        return out
        
    
    def nagios_loop(self, count, reflist, do_sleep=False, sleep_time=61):
        now = time.time()
        buffer = open('var/pipebuffer', 'w')
        for ref in reflist:
            (obj, exit_status, output) = ref
            if obj.my_type == 'service':
                cmd = "[%lu] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%d;%s\n" % (now, obj.host_name, obj.service_description, exit_status, output)
                print cmd
                buffer.write(cmd)
            else:
                cmd = "[%lu] PROCESS_HOST_CHECK_RESULT;%s;%d;%s\n" % (now, obj.host_name, exit_status, output)
                buffer.write(cmd)
        buffer.close()
        print "open pipe", self.conf.command_file
        fifo = open('var/nagios.cmd', 'w')
        cmd = "[%lu] PROCESS_FILE;%s;0\n" % (now, 'var/pipebuffer')
        fifo.write(cmd)
        fifo.flush()
        fifo.close()
        time.sleep(5)


    def nagios_extcmd(self, cmd):
        fifo = open('var/nagios.cmd', 'w')
        fifo.write(cmd)
        fifo.flush()
        fifo.close()
        time.sleep(5)



class TestConfigSmall(TestConfig):
    def setUp(self):
        self.setup_with_file('etc/nagios_1r_1h_1s.cfg')
        Comment.id = 1
        self.testid = str(os.getpid() + random.randint(1, 1000))
        self.livelogs = 'tmp/livelogs.db' + self.testid
        self.pnp4nagios = 'tmp/pnp4nagios_test' + self.testid
        self.livestatus_broker = Livestatus_broker(modconf, '127.0.0.1', str(50000 + os.getpid()), 'live', [], self.livelogs, 365, self.pnp4nagios)
        self.livestatus_broker.create_queues()
        #self.livestatus_broker.properties = {
        #    'to_queue' : 0,
        #    'from_queue' : 0
        #
        #    }
        self.livestatus_broker.init()
        print "Cleaning old broks?"
        self.sched.fill_initial_broks()
        self.update_broker()
        self.nagios_path = None
        self.livestatus_path = None
        self.nagios_config = None



    def tearDown(self):
        self.stop_nagios()
        self.livestatus_broker.dbconn.commit()
        self.livestatus_broker.dbconn.close()
        if os.path.exists(self.livelogs):
            os.remove(self.livelogs)
        if os.path.exists(self.pnp4nagios):
            shutil.rmtree(self.pnp4nagios)
        if os.path.exists('var/nagios.log'):
            os.remove('var/nagios.log')
        if os.path.exists('var/retention.dat'):
            os.remove('var/retention.dat')
        if os.path.exists('var/status.dat'):
            os.remove('var/status.dat')
        to_del = [attr for attr in self.livestatus_broker.livestatus.__class__.out_map['Host'].keys() if attr.startswith('host_')]
        for attr in to_del:
            del self.livestatus_broker.livestatus.__class__.out_map['Host'][attr]
        self.livestatus_broker = None


    def test_childs(self):
        if self.nagios_installed():
            self.start_nagios('1r_1h_1s')
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hosts
Columns: childs
Filter: name = test_host_0
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response 
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))
        request = """GET hosts
Columns: childs
Filter: name = test_router_0
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))



    def test_servicesbyhostgroup(self):
        if self.nagios_installed():
            self.start_nagios('1r_1h_1s')
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET servicesbyhostgroup
Filter: host_groups >= allhosts
Columns: hostgroup_name host_name service_description groups
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

        # Again, but without filter
        request = """GET servicesbyhostgroup
Columns: hostgroup_name host_name service_description groups
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))


    def test_hostsbygroup(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('1r_1h_1s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hostsbygroup
ColumnHeaders: on
Columns: host_name hostgroup_name
Filter: groups >= allhosts
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))


    def test_status(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('1r_1h_1s')
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
        self.scheduler_loop(2, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 2, 'BAD']])
        self.update_broker(True)
        #---------------------------------------------------------------
        # get the full hosts table
        #---------------------------------------------------------------
        request = 'GET hosts'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            # todo 1 != 1.0000000000e+00
            #self.assert_(self.lines_equal(response, nagresponse))

        #---------------------------------------------------------------
        # get only the host names and addresses
        #---------------------------------------------------------------
        request = 'GET hosts\nColumns: name address groups\nColumnHeaders: on'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

        #---------------------------------------------------------------
        # query_1
        #---------------------------------------------------------------
        request = 'GET contacts'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_1_______________\n%s\n%s\n' % (request, response)
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            # There are some sick columns in the livestatus response like
            # modified_attributes;modified_attributes_list
            # These are not implemented in shinken-livestatus (never, i think)
            #self.assert_(self.lines_equal(response, nagresponse))

        #---------------------------------------------------------------
        # query_2
        #---------------------------------------------------------------
        request = 'GET contacts\nColumns: name alias'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_2_______________\n%s\n%s\n' % (request, response)
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

        #---------------------------------------------------------------
        # query_3
        #---------------------------------------------------------------
        #self.scheduler_loop(3, svc, 2, 'BAD')
        request = 'GET services\nColumns: host_name description state\nFilter: state = 2\nColumnHeaders: on'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_3_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == 'host_name;description;state\ntest_host_0;test_ok_0;2\n')
        request = 'GET services\nColumns: host_name description state\nFilter: state = 2'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_3_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == 'test_host_0;test_ok_0;2\n')
        request = 'GET services\nColumns: host_name description state\nFilter: state = 0'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_3_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == '\n')
        duration = 180
        now = time.time()
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;0;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self.sched.run_external_command(cmd)
        self.update_broker(True)
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        self.update_broker(True)
        self.scheduler_loop(3, [[svc, 2, 'BAD']])
        self.update_broker(True)
        request = 'GET services\nColumns: host_name description scheduled_downtime_depth\nFilter: state = 2\nFilter: scheduled_downtime_depth = 1'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_3_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == 'test_host_0;test_ok_0;1\n')

        #---------------------------------------------------------------
        # query_4
        #---------------------------------------------------------------
        request = 'GET services\nColumns: host_name description state\nFilter: state = 2\nFilter: in_notification_period = 1\nAnd: 2\nFilter: state = 0\nOr: 2\nFilter: host_name = test_host_0\nFilter: description = test_ok_0\nAnd: 3\nFilter: contacts >= harri\nFilter: contacts >= test_contact\nOr: 3'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_4_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == 'test_host_0;test_ok_0;2\n')

        #---------------------------------------------------------------
        # query_6
        #---------------------------------------------------------------
        request = 'GET services\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_6_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == '0;0;1;0\n')

        #---------------------------------------------------------------
        # query_7
        #---------------------------------------------------------------
        request = 'GET services\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\nFilter: contacts >= test_contact'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_6_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == '0;0;1;0\n')
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            # TODO looks like a timing problem with nagios
            #self.assert_(self.lines_equal(response, nagresponse))


    def test_json(self):
        self.print_header()
        print "got initial broks"
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
        self.scheduler_loop(2, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 2, 'BAD']])
        self.update_broker()
        request = 'GET services\nColumns: host_name description state\nOutputFormat: json'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'json wo headers__________\n%s\n%s\n' % (request, response)
        self.assert_(response == '[["test_host_0","test_ok_0",2]]\n')
        request = 'GET services\nColumns: host_name description state\nOutputFormat: json\nColumnHeaders: on'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'json with headers__________\n%s\n%s\n' % (request, response)
        self.assert_(response == '[["host_name","description","state"],["test_host_0","test_ok_0",2]]\n')
        #100% mklivesttaus: self.assert_(response == '[["host_name","description","state"],\n["test_host_0","test_ok_0",2]]\n')


    def test_thruk(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('1r_1h_1s')
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
        self.scheduler_loop(2, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 2, 'BAD']])
        self.update_broker()
        #---------------------------------------------------------------
        # get the full hosts table
        #---------------------------------------------------------------
        request = """GET hosts
Stats: name !=
Stats: check_type = 0
Stats: check_type = 1
Stats: has_been_checked = 1
Stats: state = 0
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 1
StatsAnd: 2
Stats: has_been_checked = 1
Stats: state = 2
StatsAnd: 2
Stats: has_been_checked = 0
Stats: has_been_checked = 0
Stats: active_checks_enabled = 0
StatsAnd: 2
Stats: has_been_checked = 0
Stats: scheduled_downtime_depth > 0
StatsAnd: 2
Stats: state = 0
Stats: has_been_checked = 1
Stats: active_checks_enabled = 0
StatsAnd: 3
Stats: state = 0
Stats: has_been_checked = 1
Stats: scheduled_downtime_depth > 0
StatsAnd: 3
Stats: state = 1
Stats: has_been_checked = 1
Stats: acknowledged = 1
StatsAnd: 3
Stats: state = 1
Stats: scheduled_downtime_depth > 0
Stats: has_been_checked = 1
StatsAnd: 3
Stats: state = 1
Stats: active_checks_enabled = 0
Stats: has_been_checked = 1
StatsAnd: 3
Stats: state = 1
Stats: active_checks_enabled = 1
Stats: acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: has_been_checked = 1
StatsAnd: 5
Stats: state = 2
Stats: acknowledged = 1
Stats: has_been_checked = 1
StatsAnd: 3
Stats: state = 2
Stats: scheduled_downtime_depth > 0
Stats: has_been_checked = 1
StatsAnd: 3
Stats: state = 2
Stats: active_checks_enabled = 0
StatsAnd: 2
Stats: state = 2
Stats: active_checks_enabled = 1
Stats: acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: has_been_checked = 1
StatsAnd: 5
Stats: is_flapping = 1
Stats: flap_detection_enabled = 0
Stats: notifications_enabled = 0
Stats: event_handler_enabled = 0
Stats: active_checks_enabled = 0
Stats: accept_passive_checks = 0
Stats: state = 1
Stats: childs !=
StatsAnd: 2
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            # TODO timing problem?
            #self.assert_(self.lines_equal(response, nagresponse))
        
        request = """GET comments
Columns: host_name source type author comment entry_time entry_type expire_time
Filter: service_description ="""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

        request = """GET hosts
Columns: comments has_been_checked state name address acknowledged notifications_enabled active_checks_enabled is_flapping scheduled_downtime_depth is_executing notes_url_expanded action_url_expanded icon_image_expanded icon_image_alt last_check last_state_change plugin_output next_check long_plugin_output
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response

        duration = 180
        now = time.time()
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_warning_00;%d;%d;0;0;%d;lausser;blablubsvc" % (now, now, now + duration, duration)
        print cmd
        self.sched.run_external_command(cmd)
        if self.nagios_installed():
            self.nagios_extcmd(cmd)
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;0;0;%d;lausser;blablubhost" % (now, now, now + duration, duration)
        print cmd
        self.sched.run_external_command(cmd)
        if self.nagios_installed():
            self.nagios_extcmd(cmd)
        self.update_broker()
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        self.update_broker()
        self.scheduler_loop(3, [[svc, 2, 'BAD']])
        self.update_broker()
        request = """GET downtimes
Filter: service_description =
Columns: author comment end_time entry_time fixed host_name id start_time
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            #time.sleep(10)
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            #TODO the entry_times are different. find a way to round the numbers
            # so that they are equal
            #self.assert_(self.lines_equal(response, nagresponse))

        request = """GET comments
Filter: service_description =
Columns: author comment
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            time.sleep(10)
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            #self.assert_(self.lines_equal(response, nagresponse))

        request = """GET services
Filter: has_been_checked = 1
Filter: check_type = 0
Stats: sum has_been_checked
Stats: sum latency
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response

        request = """GET services
Filter: has_been_checked = 1
Filter: check_type = 0
Stats: sum has_been_checked
Stats: sum latency
Stats: sum execution_time
Stats: min latency
Stats: min execution_time
Stats: max latency
Stats: max execution_time
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response

        request = """GET services\nFilter: has_been_checked = 1\nFilter: check_type = 0\nStats: sum has_been_checked as has_been_checked\nStats: sum latency as latency_sum\nStats: sum execution_time as execution_time_sum\nStats: min latency as latency_min\nStats: min execution_time as execution_time_min\nStats: max latency as latency_max\nStats: max execution_time as execution_time_max\n\nResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response

        request = """GET hostgroups\nColumnHeaders: on\nResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            # TODO members_with_state
            #self.assert_(self.lines_equal(response, nagresponse))

        request = """GET hosts\nColumns: name groups\nColumnHeaders: on\nResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

        request = """GET hostgroups\nColumns: name num_services num_services_ok\nColumnHeaders: on\nResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

        request = """GET hostgroups\nColumns: name num_services_pending num_services_ok num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nColumnHeaders: on\nResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response

        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']])
        self.update_broker()
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()

        print "WARNING SOFT;1"
        # worst_service_state 1, worst_service_hard_state 0
        request = """GET hostgroups\nColumns: name num_services_pending num_services_ok num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nColumnHeaders: on\nResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()
        print "WARNING HARD;3"
        # worst_service_state 1, worst_service_hard_state 1
        request = """GET hostgroups\nColumns: name num_services_pending num_services_ok num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nColumnHeaders: on\nResponseHeader: fixed16"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        for s in self.livestatus_broker.livestatus.services.values():
            print "%s %d %s;%d" % (s.state, s.state_id, s.state_type, s.attempt)


    def test_thruk_config(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('1r_1h_1s')
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
        self.scheduler_loop(2, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 2, 'BAD']])
        self.update_broker()
        #---------------------------------------------------------------
        # get the full hosts table
        #---------------------------------------------------------------
        request = 'GET status\nColumns: livestatus_version program_version accept_passive_host_checks accept_passive_service_checks check_external_commands check_host_freshness check_service_freshness enable_event_handlers enable_flap_detection enable_notifications execute_host_checks execute_service_checks last_command_check last_log_rotation nagios_pid obsess_over_hosts obsess_over_services process_performance_data program_start interval_length'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response



    def test_thruk_comments(self):
        self.print_header()
        host = self.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = [] # ignore the router
        router = self.sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = [] # ignore the router
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        duration = 600
        now = time.time()
        # downtime valid for the next 2 minutes
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self.sched.run_external_command(cmd)
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)

        print "downtime was scheduled. check its activity and the comment"
        self.assert_(len(self.sched.downtimes) == 1)
        self.assert_(len(svc.downtimes) == 1)
        self.assert_(svc.downtimes[0] in self.sched.downtimes.values())
        self.assert_(svc.downtimes[0].fixed)
        self.assert_(svc.downtimes[0].is_in_effect)
        self.assert_(not svc.downtimes[0].can_be_deleted)
        self.assert_(len(self.sched.comments) == 1)
        self.assert_(len(svc.comments) == 1)
        self.assert_(svc.comments[0] in self.sched.comments.values())
        self.assert_(svc.downtimes[0].comment_id == svc.comments[0].id)

        now = time.time()
        cmd = "[%lu] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;lausser;comment" % now
        self.sched.run_external_command(cmd)
        #cmd = "[%lu] ADD_HOST_COMMENT;test_host_0;1;lausser;hcomment" % now
        #self.sched.run_external_command(cmd)
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.assert_(len(self.sched.comments) == 2)
        self.assert_(len(svc.comments) == 2)

        self.update_broker()
        svc_comment_list = (',').join([str(c.id) for c in svc.comments])

        #request = """GET comments\nColumns: host_name service_description id source type author comment entry_time entry_type persistent expire_time expires\nFilter: service_description !=\nResponseHeader: fixed16\nOutputFormat: json\n"""
        request = """GET services\nColumns: comments host_comments host_is_executing is_executing\nFilter: service_description !=\nResponseHeader: fixed16\nOutputFormat: json\n"""
        response, _ = self.livestatus_broker.livestatus.handle_request(request)
#        print response
        good_response = """200          17
[[[""" + svc_comment_list +"""],[],0,0]]
"""
        self.assert_(response == good_response) # json

        request = """GET services\nColumns: comments host_comments host_is_executing is_executing\nFilter: service_description !=\nResponseHeader: fixed16\n"""
        response, _ = self.livestatus_broker.livestatus.handle_request(request)
#        print response
        good_response = """200           9
""" + svc_comment_list + """;;0;0
"""
        self.assert_(response == good_response) # csv

        request = """GET comments\n\
Columns: author entry_type expires expire_time host_name id persistent service_description source type\n\
Filter: service_description !=\n\
Filter: service_description =\n\
Or: 2\n\
OutputFormat: json\n\
ResponseHeader: fixed16\n"""
        response, _ = self.livestatus_broker.livestatus.handle_request(request)
        good_response = """200         115
[["(Nagios Process)",2,0,0,"test_host_0",1,0,"test_ok_0",0,2],["lausser",1,0,0,"test_host_0",2,1,"test_ok_0",1,2]]
"""
        self.assert_(response == good_response)


    def test_thruk_logs(self):
        self.print_header()
        start = time.time()
        host = self.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = [] # ignore the router
        router = self.sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = [] # ignore the router
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()
        duration = 600
        now = time.time()
        # downtime valid for the next 2 minutes
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self.sched.run_external_command(cmd)
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        now = time.time()
        cmd = "[%lu] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;lausser;comment" % now
        self.sched.run_external_command(cmd)
        time.sleep(1)
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        time.sleep(1)
        self.scheduler_loop(3, [[host, 2, 'DOWN'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        time.sleep(1)
        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        end = time.time()

        # show history for service
        request = """GET log
Columns: time type options state
Filter: time >= """ + str(int(start)) + """
Filter: time <= """ + str(int(end)) + """
Filter: type = SERVICE ALERT
Filter: type = HOST ALERT
Filter: type = SERVICE FLAPPING ALERT
Filter: type = HOST FLAPPING ALERT
Filter: type = SERVICE DOWNTIME ALERT
Filter: type = HOST DOWNTIME ALERT
Or: 6
Filter: host_name = test_host_0
Filter: service_description = test_ok_0
And: 3
Filter: type ~ starting...
Filter: type ~ shutting down...
Or: 3
Filter: current_service_description !=

Filter: service_description =
Filter: host_name !=
And: 2
Filter: service_description =
Filter: host_name =
And: 2
Or: 3"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.contains_line(response, 'SERVICE DOWNTIME ALERT;test_host_0;test_ok_0;STARTED; Service has entered a period of scheduled downtime'))


    def test_thruk_logs_alerts_summary(self):
        self.print_header()
        start = time.time()
        host = self.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = [] # ignore the router
        router = self.sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = [] # ignore the router
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()
        duration = 600
        now = time.time()
        # downtime valid for the next 2 minutes
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self.sched.run_external_command(cmd)
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        now = time.time()
        cmd = "[%lu] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;lausser;comment" % now
        self.sched.run_external_command(cmd)
        time.sleep(1)
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        time.sleep(1)
        self.scheduler_loop(3, [[host, 2, 'DOWN'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        time.sleep(1)
        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        end = time.time()

        # is this an error in thruk?

        request = """GET log
Filter: options ~ ;HARD;
Filter: type = HOST ALERT
Filter: time >= 1284056080
Filter: time <= 1284660880
Filter: current_service_description !=
Filter: service_description =
Filter: host_name !=
And: 2
Filter: service_description =
Filter: host_name =
And: 2
Or: 3
Columns: time state state_type host_name service_description current_host_groups current_service_groups plugin_output"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response


    def test_thruk_logs_current(self):
        self.print_header()
        start = time.time()
        host = self.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = [] # ignore the router
        router = self.sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = [] # ignore the router
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()
        duration = 600
        now = time.time()
        # downtime valid for the next 2 minutes
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self.sched.run_external_command(cmd)
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        now = time.time()
        cmd = "[%lu] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;lausser;comment" % now
        self.sched.run_external_command(cmd)
        time.sleep(1)
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        time.sleep(1)
        self.scheduler_loop(3, [[host, 2, 'DOWN'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        time.sleep(1)
        self.scheduler_loop(3, [[host, 0, 'UUP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
#        time.sleep(1)
#        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 2, 'DOWN'], [svc, 0, 'OK']], do_sleep=False)
#        self.update_broker()
        end = time.time()

        # show history for service
        request = """GET log
Columns: time type options state current_host_name
Filter: time >= """ + str(int(start)) + """
Filter: time <= """ + str(int(end)) + """
Filter: type = SERVICE ALERT
Filter: type = HOST ALERT
Filter: type = SERVICE FLAPPING ALERT
Filter: type = HOST FLAPPING ALERT
Filter: type = SERVICE DOWNTIME ALERT
Filter: type = HOST DOWNTIME ALERT
Or: 6
Filter: current_host_name = test_host_0
Filter: current_service_description = test_ok_0
And: 2"""
        request = """GET log
Columns: time type options state current_host_name
Filter: time >= """ + str(int(start)) + """
Filter: time <= """ + str(int(end)) + """
Filter: current_host_name = test_host_0
Filter: current_service_description = test_ok_0
And: 2"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response


    def test_thruk_tac_svc(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('1r_1h_1s')
        self.update_broker()

        start = time.time()
        host = self.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = [] # ignore the router
        router = self.sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = [] # ignore the router
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()
        duration = 600
        now = time.time()
        # downtime valid for the next 2 minutes
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;1;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self.sched.run_external_command(cmd)
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        now = time.time()
        cmd = "[%lu] ADD_SVC_COMMENT;test_host_0;test_ok_0;1;lausser;comment" % now
        self.sched.run_external_command(cmd)
        time.sleep(1)
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        time.sleep(1)
        self.scheduler_loop(3, [[host, 2, 'DOWN'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
        time.sleep(1)
        self.scheduler_loop(3, [[host, 0, 'UUP'], [router, 0, 'UP'], [svc, 0, 'OK']], do_sleep=False)
        self.update_broker()
#        time.sleep(1)
#        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 2, 'DOWN'], [svc, 0, 'OK']], do_sleep=False)
#        self.update_broker()
        end = time.time()

        # show history for service
        request = """GET services
Filter: has_been_checked = 1
Filter: check_type = 0
Stats: sum has_been_checked
Stats: sum latency
Stats: sum execution_time
Stats: min latency
Stats: min execution_time
Stats: max latency
Stats: max execution_time"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        # nagios comparison makes no sense, because the latencies/execution times will surely differ
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
        #    print nagresponse
        #    self.assert_(self.lines_equal(response, nagresponse))


    def test_columns(self):
        self.print_header()
        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        request = """GET columns"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response


    def test_scheduler_table(self):
        self.print_header()
        self.update_broker()

        creation_tab = {'scheduler_name' : 'scheduler-1', 'address' : 'localhost', 'spare' : '0'}
        schedlink = SchedulerLink(creation_tab)
        schedlink.pythonize()
        schedlink.alive = True
        b = schedlink.get_initial_status_brok()
        self.sched.add(b)
        creation_tab = {'scheduler_name' : 'scheduler-2', 'address' : 'othernode', 'spare' : '1'}
        schedlink = SchedulerLink(creation_tab)
        schedlink.pythonize()
        schedlink.alive = True
        b2 = schedlink.get_initial_status_brok()
        self.sched.add(b2)

        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        request = """GET schedulers"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """address;alive;name;port;spare;weight
othernode;1;scheduler-2;7768;1;1
localhost;1;scheduler-1;7768;0;1
"""
        print response, 'FUCK'
        print "FUCK", response, "TOTO"
        self.assert_(self.lines_equal(response, good_response))

        #Now we update a scheduler state and we check
        #here the N2
        schedlink.alive = False
        b = schedlink.get_update_status_brok()
        self.sched.add(b)
        self.update_broker()
        request = """GET schedulers"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        good_response = """address;alive;name;port;spare;weight
othernode;0;scheduler-2;7768;1;1
localhost;1;scheduler-1;7768;0;1
"""
        self.assert_(self.lines_equal(response, good_response))



    def test_reactionner_table(self):
        self.print_header()
        self.update_broker()
        creation_tab = {'reactionner_name' : 'reactionner-1', 'address' : 'localhost', 'spare' : '0'}
        reac = ReactionnerLink(creation_tab)
        reac.pythonize()
        reac.alive = True
        b = reac.get_initial_status_brok()
        self.sched.add(b)
        creation_tab = {'reactionner_name' : 'reactionner-2', 'address' : 'othernode', 'spare' : '1'}
        reac = ReactionnerLink(creation_tab)
        reac.pythonize()
        reac.alive = True
        b2 = reac.get_initial_status_brok()
        self.sched.add(b2)

        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        request = """GET reactionners"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """address;alive;name;port;spare
localhost;1;reactionner-1;7769;0
othernode;1;reactionner-2;7769;1
"""
        print response == good_response
        self.assert_(self.lines_equal(response, good_response))

        #Now the update part
        reac.alive = False
        b2 = reac.get_update_status_brok()
        self.sched.add(b2)
        self.update_broker()
        request = """GET reactionners"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """address;alive;name;port;spare
localhost;1;reactionner-1;7769;0
othernode;0;reactionner-2;7769;1
"""
        print response == good_response
        self.assert_(self.lines_equal(response, good_response))



    def test_poller_table(self):
        self.print_header()
        self.update_broker()

        creation_tab = {'poller_name' : 'poller-1', 'address' : 'localhost', 'spare' : '0'}
        pol = PollerLink(creation_tab)
        pol.pythonize()
        pol.alive = True
        b = pol.get_initial_status_brok()
        self.sched.add(b)
        creation_tab = {'poller_name' : 'poller-2', 'address' : 'othernode', 'spare' : '1'}
        pol = PollerLink(creation_tab)
        pol.pythonize()
        pol.alive = True
        b2 = pol.get_initial_status_brok()
        self.sched.add(b2)

        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        request = """GET pollers"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """address;alive;name;port;spare
localhost;1;poller-1;7771;0
othernode;1;poller-2;7771;1
"""
        print response == good_response
        self.assert_(self.lines_equal(response, good_response))

        #Now the update part
        pol.alive = False
        b2 = pol.get_update_status_brok()
        self.sched.add(b2)

        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        request = """GET pollers"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """address;alive;name;port;spare
localhost;1;poller-1;7771;0
othernode;0;poller-2;7771;1
"""
        print response == good_response
        self.assert_(self.lines_equal(response, good_response))



    def test_broker_table(self):
        self.print_header()
        self.update_broker()

        creation_tab = {'broker_name' : 'broker-1', 'address' : 'localhost', 'spare' : '0'}
        pol = BrokerLink(creation_tab)
        pol.pythonize()
        pol.alive = True
        b = pol.get_initial_status_brok()
        self.sched.add(b)
        creation_tab = {'broker_name' : 'broker-2', 'address' : 'othernode', 'spare' : '1'}
        pol = BrokerLink(creation_tab)
        pol.pythonize()
        pol.alive = True
        b2 = pol.get_initial_status_brok()
        self.sched.add(b2)

        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        request = """GET brokers"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """address;alive;name;port;spare
localhost;1;broker-1;7772;0
othernode;1;broker-2;7772;1
"""
        print response == good_response
        self.assert_(self.lines_equal(response, good_response))

        #Now the update part
        pol.alive = False
        b2 = pol.get_initial_status_brok()
        self.sched.add(b2)

        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        request = """GET brokers"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """address;alive;name;port;spare
localhost;1;broker-1;7772;0
othernode;0;broker-2;7772;1
"""
        print response == good_response
        self.assert_(self.lines_equal(response, good_response))



    def test_problems_table(self):
        self.print_header()
        self.update_broker()
        host = self.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = [] # ignore the router
        router = self.sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = [] # ignore the router
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.scheduler_loop(4, [[host, 2, 'DOWN'], [router, 2, 'DOWN'], [svc, 2, 'BAD']])
        print "Is router a problem?", router.is_problem, router.state, router.state_type
        print "Is host a problem?", host.is_problem, host.state, host.state_type
        print "Is service a problem?", svc.is_problem, svc.state, svc.state_type
        self.update_broker()
        print "All", self.livestatus_broker.hosts
        for h in self.livestatus_broker.hosts.values():
            print h.get_dbg_name(), h.is_problem

        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        request = """GET problems"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "FUCK", response
        good_response = """impacts;source
test_host_0,test_host_0/test_ok_0;test_router_0
"""
        print response == good_response
        self.assert_(response == good_response)


    def test_parent_childs_dep_lists(self):
        self.print_header()
        self.update_broker()
        host = self.sched.hosts.find_by_name("test_host_0")
        router = self.sched.hosts.find_by_name("test_router_0")
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        # first test if test_router_0 is in the host parent list
        request = 'GET hosts\nColumns: host_name parent_dependencies\nFilter: host_name = test_host_0\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        good_response = """test_host_0;test_router_0"""
        self.assert_(response.strip() == good_response.strip())

        # Now check if host is in the child router list
        request = 'GET hosts\nColumns: host_name child_dependencies\nFilter: host_name = test_router_0\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        good_response = """test_router_0;test_host_0"""
        self.assert_(response.strip() == good_response.strip())

        # Now check with the service
        request = 'GET hosts\nColumns: host_name child_dependencies\nFilter: host_name = test_host_0\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        good_response = """test_host_0;test_host_0/test_ok_0"""
        self.assert_(response.strip() == good_response.strip())

        # And check the parent for the service
        request = 'GET services\nColumns: parent_dependencies\nFilter: host_name = test_host_0\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        good_response = """test_host_0"""
        self.assert_(response.strip() == good_response.strip())


    def test_limit(self):
        self.print_header() 
        if self.nagios_installed():
            self.start_nagios('1r_1h_1s')
        now = time.time()
        self.update_broker()
        #---------------------------------------------------------------
        # get the full hosts table
        #---------------------------------------------------------------
        request = 'GET hosts\nColumns: host_name\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """test_host_0
test_router_0
"""
        self.assert_(self.lines_equal(response, good_response))

        request = 'GET hosts\nColumns: host_name\nLimit: 1\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """test_host_0
"""
        # it must be test_host_0 because with Limit: the output is 
        # alphabetically ordered
        self.assert_(response == good_response)
        # TODO look whats wrong
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
        #    print nagresponse
        #    self.assert_(self.lines_equal(response, nagresponse))



    def test_problem_impact_in_host_service(self):
        self.print_header() 
        now = time.time()
        self.update_broker()

        host_router_0 = self.sched.hosts.find_by_name("test_router_0")
        host_router_0.checks_in_progress = []

        #Then initialize host under theses routers
        host_0 = self.sched.hosts.find_by_name("test_host_0")
        host_0.checks_in_progress = []

        all_hosts = [host_router_0, host_0]
        all_routers = [host_router_0]
        all_servers = [host_0]

        print "- 4 x UP -------------------------------------"
        self.scheduler_loop(1, [[host_router_0, 0, 'UP'], [host_0, 0, 'UP']], do_sleep=False)
        self.scheduler_loop(1, [[host_router_0, 1, 'DOWN']], do_sleep=False)
        self.scheduler_loop(1, [[host_router_0, 1, 'DOWN']], do_sleep=False)
        self.scheduler_loop(1, [[host_router_0, 1, 'DOWN']], do_sleep=False)
        self.scheduler_loop(1, [[host_router_0, 1, 'DOWN']], do_sleep=False)
        self.scheduler_loop(1, [[host_router_0, 1, 'DOWN']], do_sleep=False)

        #Max attempt is reach, should be HARD now
        for h in all_routers:
            self.assert_(h.state == 'DOWN')
            self.assert_(h.state_type == 'HARD')

        for b in self.sched.broks.values():
            print "All broks", b.type, b
            if b.type == 'update_host_status':
                print "***********"
                print "Impacts", b.data['impacts']
                print "Sources",  b.data['source_problems']

        for b in host_router_0.broks:
            print " host_router_0.broks", b

        self.update_broker()
        
        print "source de host_0", host_0.source_problems
        for i in host_0.source_problems:
            print "source", i.get_name()
        print "impacts de host_router_0", host_router_0.impacts
        for i in host_router_0.impacts:
            print "impact", i.get_name()

        #---------------------------------------------------------------
        # get the full hosts table
        #---------------------------------------------------------------
        print "Got source problems"
        request = 'GET hosts\nColumns: host_name is_impact source_problems\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "moncullulu2", response
        good_response = """test_router_0;0;
test_host_0;1;test_router_0
"""
        #self.assert_(self.lines_equal(response, good_response))

        print "Now got impact"
        request = 'GET hosts\nColumns: host_name is_problem impacts\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "moncululu", response
        good_response = """test_router_0;1;test_host_0,test_host_0/test_ok_0
test_host_0;0;"""
        self.assert_(self.lines_equal(response.strip(), good_response.strip()))

        request = 'GET hosts\nColumns: host_name\nLimit: 1\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        good_response = """test_host_0
"""
        # it must be test_host_0 because with Limit: the output is 
        # alphabetically ordered
        self.assert_(response == good_response)



    def test_thruk_servicegroup(self):
        self.print_header()
        now = time.time()
        self.update_broker()
        #---------------------------------------------------------------
        # get services of a certain servicegroup
        # test_host_0/test_ok_0 is in 
        #   servicegroup_01,ok via service.servicegroups
        #   servicegroup_02 via servicegroup.members
        #---------------------------------------------------------------
        request = """GET services
Columns: host_name service_description
Filter: groups >= servicegroup_01
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assert_(response == """200          22
test_host_0;test_ok_0
""")
        request = """GET services
Columns: host_name service_description
Filter: groups >= servicegroup_02
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assert_(response == """200          22
test_host_0;test_ok_0
""")



    def test_is_executing(self):
        self.print_header()
        #---------------------------------------------------------------
        # make sure that the is_executing flag is updated regularly
        #---------------------------------------------------------------
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

        for loop in range(1, 2):
            print "processing check", loop
            self.show_broks("update_in_checking")
            svc.update_in_checking()
            self.show_broks("fake_check")
            self.fake_check(svc, 2, 'BAD')
            self.show_broks("sched.consume_results")
            self.sched.consume_results()
            self.show_broks("sched.get_new_actions")
            self.sched.get_new_actions()
            self.show_broks("sched.get_new_broks")
            self.sched.get_new_broks()
            self.show_broks("sched.delete_zombie_checks")
            self.sched.delete_zombie_checks()
            self.show_broks("sched.delete_zombie_actions")
            self.sched.delete_zombie_actions()
            self.show_broks("sched.get_to_run_checks")
            checks = self.sched.get_to_run_checks(True, False)
            self.show_broks("sched.get_to_run_checks")
            actions = self.sched.get_to_run_checks(False, True)
            #self.show_actions()
            for a in actions:
                a.status = 'inpoller'
                a.check_time = time.time()
                a.exit_status = 0
                self.sched.put_results(a)
            #self.show_actions()

            svc.checks_in_progress = []
            self.show_broks("sched.update_downtimes_and_comments")
            self.sched.update_downtimes_and_comments()
            time.sleep(5)

        print "-------------------------------------------------"
        for brok in sorted(self.sched.broks.values(), lambda x, y: x.id - y.id):
            if re.compile('^service_').match(brok.type):
                print "BROK:", brok.type
                print "BROK   ", brok.data['in_checking']
        self.update_broker()
        print "-------------------------------------------------"
        request = 'GET services\nColumns: service_description is_executing\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        


    def test_pnp_path(self):
        self.print_header()
        now = time.time()
        self.update_broker()
        #---------------------------------------------------------------
        # pnp_path is a parameter for the module
        # column pnpgraph_present checks if a file
        #  <pnp_path>/host/service.xml
        #  <pnp_path>/host/_HOST_.xml
        # exists
        #---------------------------------------------------------------
        pnp_path = self.pnp4nagios
        try:
            os.removedirs(pnp_path)
        except:
            pass
        else:
            print "there is no spool dir", pnp_path

        request = """GET services
Columns: host_name service_description pnpgraph_present
OutputFormat: csv
ResponseHeader: fixed16
"""
        requesth = """GET hosts
Columns: host_name pnpgraph_present
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == """200          24
test_host_0;test_ok_0;0
""")
        #self.assert_(not self.livestatus_broker.livestatus.pnp_path)

        try:
            os.makedirs(pnp_path)
            print "there is an empty spool dir", pnp_path
        except:
            pass
        
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == """200          24
test_host_0;test_ok_0;0
""")
        self.assert_(self.livestatus_broker.livestatus.pnp_path == pnp_path + '/')

        try:
            os.makedirs(pnp_path + '/test_host_0')
            open(pnp_path + '/test_host_0/_HOST_.xml', 'w').close() 
            open(pnp_path + '/test_host_0/test_ok_0.xml', 'w').close() 
            print "there is a spool dir with data", pnp_path
        except:
            pass
        
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == """200          24
test_host_0;test_ok_0;1
""")
        response, keepalive = self.livestatus_broker.livestatus.handle_request(requesth)
        print response
        goodresponse = """200          30
test_router_0;0
test_host_0;1
"""
        self.assert_(self.lines_equal(response, goodresponse))


    def test_thruk_action_notes_url_icon_image(self):
        self.print_header()
        now = time.time()
        self.update_broker()
        request = """GET services
Columns: host_name service_description action_url
Filter: host_name = test_host_0
Filter: service_description = test_ok_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assert_(response == """200          78
test_host_0;test_ok_0;/nagios/pnp/index.php?host=$HOSTNAME$&srv=$SERVICEDESC$
""")

        request = """GET services
Columns: host_name service_description action_url_expanded
Filter: host_name = test_host_0
Filter: service_description = test_ok_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assert_(response == """200          75
test_host_0;test_ok_0;/nagios/pnp/index.php?host=test_host_0&srv=test_ok_0
""")

        request = """GET services
Columns: host_name service_description icon_image_expanded
Filter: host_name = test_host_0
Filter: service_description = test_ok_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == """200          79
test_host_0;test_ok_0;../../docs/images/tip.gif?host=test_host_0&srv=test_ok_0
""")

        request = """GET services
Columns: host_name service_description notes_url_expanded
Filter: host_name = test_host_0
Filter: service_description = test_ok_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == """200          66
test_host_0;test_ok_0;/nagios/wiki/doku.php/test_host_0/test_ok_0
""")

        request = """GET hosts
Columns: host_name action_url_expanded
Filter: host_name = test_host_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == """200          51
test_host_0;/nagios/pnp/index.php?host=test_host_0
""")

        request = """GET hosts
Columns: host_name icon_image_expanded
Filter: host_name = test_router_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == """200          62
test_router_0;../../docs/images/switch.png?host=test_router_0
""")

        request = """GET hosts
Columns: host_name notes_url_expanded
Filter: host_name = test_host_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == """200          46
test_host_0;/nagios/wiki/doku.php/test_host_0
""")


    def test_thruk_custom_variables(self):
        self.print_header()
        now = time.time()
        self.update_broker()
        request = """GET hosts
Columns: host_name custom_variable_names custom_variable_values
Filter: host_name = test_host_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assert_(response == """200          42
test_host_0;OSLICENSE,OSTYPE;gpl,gnulinux
""")

        request = """GET services
Columns: host_name service_description custom_variable_names custom_variable_values
Filter: host_name = test_host_0
Filter: service_description = test_ok_0
OutputFormat: csv
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assert_(response == """200          41
test_host_0;test_ok_0;CUSTNAME;custvalue
""")


    def test_multisite_in_check_period(self):
        self.print_header()
        self.update_broker()
        # timeperiods must be manipulated in the broker, because status-broks
        # contain timeperiod names, not objects.
        lshost = self.livestatus_broker.hosts["test_host_0"]
        now = time.time()
        localnow = time.localtime(now)
        if localnow[5] > 45:
            time.sleep(15)
        nextminute = time.localtime(time.time() + 60)
        tonextminute = '%s 00:00-%02d:%02d' % (['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][nextminute[6]], nextminute[3], nextminute[4])
        fromnextminute = '%s %02d:%02d-23:59' % (['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][nextminute[6]], nextminute[3], nextminute[4])

        lshost.notification_period = Timeperiod()
        lshost.notification_period.resolve_daterange(lshost.notification_period.dateranges, tonextminute)
        lshost.check_period = Timeperiod()
        lshost.check_period.resolve_daterange(lshost.check_period.dateranges, fromnextminute)
        self.update_broker()
        print "now it is", time.asctime()
        print "notification_period is", tonextminute
        print "check_period is", fromnextminute
        request = """GET hosts
Columns: host_name in_notification_period in_check_period
Filter: host_name = test_host_0
OutputFormat: csv
ResponseHeader: fixed16
"""

        # inside notification_period, outside check_period
        time.sleep(5)
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assert_(response == """200          16
test_host_0;1;0
""")
        time.sleep(60)
        # a minute later it's the other way round
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        self.assert_(response == """200          16
test_host_0;0;1
""")


    def test_thruk_log_current_groups(self):
        self.print_header() 
        now = time.time()
        b = Brok('log', {'log' : "[%lu] EXTERNAL COMMAND: [%lu] DISABLE_NOTIFICATIONS" % (now, now) })
        self.livestatus_broker.manage_log_brok(b)
        b = Brok('log', {'log' : "[%lu] EXTERNAL COMMAND: [%lu] STOP_EXECUTING_SVC_CHECKS" % (now, now) })
        self.livestatus_broker.manage_log_brok(b)
        self.update_broker()
        host = self.sched.hosts.find_by_name("test_host_0")
        host.checks_in_progress = []
        host.act_depend_of = [] # ignore the router
        router = self.sched.hosts.find_by_name("test_router_0")
        router.checks_in_progress = []
        router.act_depend_of = [] # ignore the router
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        svc.checks_in_progress = []
        svc.act_depend_of = [] # no hostchecks on critical checkresults
        self.update_broker()
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()
        # select messages which are not host or service related. current_service_groups must be an empty list
        request = """GET log
Filter: current_host_name =
Filter: current_service_description =
And: 2
Columns: message current_service_groups
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        request = """GET log
Filter: current_host_name =
Filter: current_service_description =
And: 2
Columns: message current_service_groups
OutputFormat: json
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        good_response = "[[\"[%lu] EXTERNAL COMMAND: [%lu] DISABLE_NOTIFICATIONS\",[]],[\"[%lu] EXTERNAL COMMAND: [%lu] STOP_EXECUTING_SVC_CHECKS\",[]]]\n" % (now, now, now, now)
        print response
        self.assert_(response == good_response)

        request = """GET log
Columns: time current_host_name current_service_description current_host_groups current_service_groups
Filter: time >= """ + str(int(now)) + """
Filter: current_host_name = test_host_0
Filter: current_service_description = test_ok_0
And: 2"""
        good_response = """1234567890;test_host_0;test_ok_0;hostgroup_01,allhosts,up;servicegroup_02,ok,servicegroup_01
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        # remove the timestamps
        good_response = ';'.join(good_response.split(';')[1:])
        response = ';'.join(response.split(';')[1:])
        print response
        self.assert_(self.lines_equal(response, good_response))


    def test_database_shrink(self):
        self.print_header()
        for cycle in xrange(10):
            for brok in xrange(100):
                now = time.time()
                b = Brok('log', {'log' : "[%lu] EXTERNAL COMMAND: [%lu] DISABLE_NOTIFICATIONS" % (now, now) })
                self.livestatus_broker.manage_log_brok(b)
            time.sleep(1)

        self.update_broker()
        self.livestatus_broker.dbcursor.execute('SELECT COUNT(*) FROM logs')
        dbrows1 = self.livestatus_broker.dbcursor.fetchone()
        response, keepalive = self.livestatus_broker.livestatus.handle_request("GET log\nColumns: time")
        rows1 = len(response.splitlines())
        size1 = os.path.getsize(self.livestatus_broker.database_file)
        # now delete log entries older than 6 seconds
        self.livestatus_broker.max_logs_age = 6.0 / 86400.0
        self.livestatus_broker.cleanup_log_db()

        self.livestatus_broker.dbcursor.execute('SELECT COUNT(*) FROM logs')
        dbrows2 = self.livestatus_broker.dbcursor.fetchone()
        response, keepalive = self.livestatus_broker.livestatus.handle_request("GET log\nColumns: time")
        rows2 = len(response.splitlines())
        size2 = os.path.getsize(self.livestatus_broker.database_file)
        print "size1", size1
        print "size2", size2
        print "rows1", rows1
        print "rows2", rows2
        print "dbrows1", dbrows1
        print "dbrows2", dbrows2
        self.assert_(rows1 == dbrows1[0])
        self.assert_(rows2 == dbrows2[0])
        self.assert_(dbrows1 > dbrows2)
        self.assert_(rows1 > rows2)
        # The most important...database file shrunk
        self.assert_(size1 > size2)


    def test_thruk_empty_stats(self):
        self.print_header()
        self.update_broker()
        # surely no host object matches with this filter
        # nonetheless there must be a line of output
        request = """GET hosts
Filter: has_been_checked = 10
Filter: check_type = 10
Stats: sum percent_state_change
Stats: min percent_state_change
Stats: max percent_state_change
OutputFormat: csv"""
        
        good_response = """0;0;0"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.lines_equal(response, good_response))


    def test_thruk_host_parents(self):
        self.print_header()
        self.update_broker()
        # surely no host object matches with this filter
        # nonetheless there must be a line of output
        request = """GET hosts
Columns: host_name parents
OutputFormat: csv"""
        
        good_response = """test_router_0;
test_host_0;test_router_0
"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.lines_equal(response, good_response))



    def test_statsgroupby(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        svc1 = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        print svc1
        self.scheduler_loop(1, [[svc1, 1, 'W']])
        self.update_broker()

        request = """GET services
Filter: contacts >= test_contact
Stats: state != 9999
Stats: state = 0
Stats: state = 1
Stats: state = 2
Stats: state = 3
StatsGroupBy: host_name"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.contains_line(response, 'test_host_0;1;0;1;0;0'))

        request = """GET services
Stats: state != 9999
StatsGroupBy: state
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        # does not show null-values
        #self.assert_(self.contains_line(response, '0;0'))
        self.assert_(self.contains_line(response, '1;1'))
        #self.assert_(self.contains_line(response, '2;0'))
        #self.assert_(self.contains_line(response, '3;0'))


    def test_multisite_column_groupby(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        router = self.sched.hosts.find_by_name("test_router_0")
        host = self.sched.hosts.find_by_name("test_host_0")
        svc = self.sched.services.find_srv_by_name_and_hostname("test_host_0", "test_ok_0")
        host.act_depend_of = []
        router.act_depend_of = []
        self.scheduler_loop(4, [[router, 1, 'D'], [host, 1, 'D'], [svc, 1, 'W']])
        self.update_broker()
        self.scheduler_loop(1, [[router, 0, 'U'], [host, 0, 'U'], [svc, 0, 'O']])
        self.update_broker()
        self.scheduler_loop(1, [[router, 1, 'D'], [host, 0, 'U'], [svc, 2, 'C']])
        self.update_broker()

        request = """GET log
Columns: host_name service_description
Filter: log_time >= 1292256802
Filter: class = 1
Stats: state = 0
Stats: state = 1
Stats: state = 2
Stats: state = 3
Stats: state != 0
OutputFormat: csv
Limit: 1001"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.contains_line(response, 'test_host_0;;1;3;0;0;3'))
        self.assert_(self.contains_line(response, 'test_router_0;;1;4;0;0;4'))
        self.assert_(self.contains_line(response, 'test_host_0;test_ok_0;1;2;1;0;3'))


        # does not show null-values
        #self.assert_(self.contains_line(response, '0;0'))
        #self.assert_(self.contains_line(response, '1;1'))
        #self.assert_(self.contains_line(response, '2;0'))
        #self.assert_(self.contains_line(response, '3;0'))


    def test_downtimes_ref(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        duration = 180
        now = time.time()
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;0;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self.sched.run_external_command(cmd)
        self.update_broker(True)
        request = 'GET downtimes\nColumns: host_name service_description id comment\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == 'test_host_0;test_ok_0;1;blablub\n')


    def test_display_name(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hosts
Filter: name = test_host_0
Columns: name display_name"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(response == 'test_host_0;test_host_0\n')
        request = """GET services
Filter: host_name = test_host_0
Filter: description = test_ok_0
Columns: description host_name display_name"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "hihi",response
        self.assert_(response == 'test_ok_0;test_host_0;test_ok_0\n')



class TestConfigBig(TestConfig):
    def setUp(self):
        start_setUp = time.time()
        self.setup_with_file('etc/nagios_5r_100h_2000s.cfg')
        Comment.id = 1
        self.testid = str(os.getpid() + random.randint(1, 1000))
        self.livelogs = 'tmp/livelogs.db' + self.testid
        self.pnp4nagios = 'tmp/pnp4nagios_test' + self.testid
        self.livestatus_broker = Livestatus_broker(modconf, '127.0.0.1', str(50000 + os.getpid()), 'live', [], self.livelogs, 365, self.pnp4nagios)
        self.livestatus_broker.create_queues()
        #self.livestatus_broker.properties = {
        #    'to_queue' : 0,
        #    'from_queue' : 0
        #}
        print "************* Intermediate SetUp:", time.time() - start_setUp
        self.livestatus_broker.init()
        print "Cleaning old broks?"
        self.sched.fill_initial_broks()
        self.update_broker()
        print "************* Overall Setup:", time.time() - start_setUp

    def tearDown(self):
        self.stop_nagios()
        self.livestatus_broker.dbconn.commit()
        self.livestatus_broker.dbconn.close()
        if os.path.exists(self.livelogs):
            os.remove(self.livelogs)
        if os.path.exists(self.pnp4nagios):
            shutil.rmtree(self.pnp4nagios)
        if os.path.exists('var/nagios.log'):
            os.remove('var/nagios.log')
        if os.path.exists('var/retention.dat'):
            os.remove('var/retention.dat')
        if os.path.exists('var/status.dat'):
            os.remove('var/status.dat')
        to_del = [attr for attr in self.livestatus_broker.livestatus.__class__.out_map['Host'].keys() if attr.startswith('host_')]
        for attr in to_del:
            del self.livestatus_broker.livestatus.__class__.out_map['Host'][attr]
        self.livestatus_broker = None


    def test_stats(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        svc1 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_00")
        print svc1
        svc2 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_15")
        print svc2
        svc3 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_16")
        print svc3
        svc4 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_05")
        print svc4
        svc5 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_11")
        svc6 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_01")
        svc7 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_03")
        self.scheduler_loop(1, [[svc1, 1, 'W'], [svc2, 1, 'W'], [svc3, 1, 'W'], [svc4, 2, 'C'], [svc5, 3, 'U'], [svc6, 2, 'C'], [svc7, 2, 'C']])
        self.update_broker()
        # 1993O, 3xW, 3xC, 1xU

        request = """GET services
Filter: contacts >= test_contact
Stats: state != 9999
Stats: state = 0
Stats: state = 1
Stats: state = 2
Stats: state = 3"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_6_______________\n%s\n%s\n' % (request, response)
        self.assert_(response == '2000;1993;3;3;1\n')

        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))


    def test_statsgroupby(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        svc1 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_00")
        print svc1
        svc2 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_15")
        print svc2
        svc3 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_16")
        print svc3
        svc4 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_05")
        print svc4
        svc5 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_11")
        svc6 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_01")
        svc7 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_03")
        self.scheduler_loop(1, [[svc1, 1, 'W'], [svc2, 1, 'W'], [svc3, 1, 'W'], [svc4, 2, 'C'], [svc5, 3, 'U'], [svc6, 2, 'C'], [svc7, 2, 'C']])
        self.update_broker()
        # 1993O, 3xW, 3xC, 1xU

        request = 'GET services\nFilter: contacts >= test_contact\nStats: state != 9999\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\nStatsGroupBy: host_name'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.contains_line(response, 'test_host_005;20;17;3;0;0'))
        self.assert_(self.contains_line(response, 'test_host_007;20;18;0;1;1'))
        self.assert_(self.contains_line(response, 'test_host_025;20;18;0;2;0'))
        self.assert_(self.contains_line(response, 'test_host_026;20;20;0;0;0'))

        request = """GET services
Stats: state != 9999
StatsGroupBy: state
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.contains_line(response, '0;1993'))
        self.assert_(self.contains_line(response, '1;3'))
        self.assert_(self.contains_line(response, '2;3'))
        self.assert_(self.contains_line(response, '3;1'))
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))


    def test_hostsbygroup(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hostsbygroup
ColumnHeaders: on
Columns: host_name hostgroup_name
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""

        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))


    def test_servicesbyhostgroup(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET servicesbyhostgroup
Filter: host_groups >= up
Stats: has_been_checked = 0
Stats: state = 0
Stats: has_been_checked != 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 4
Stats: state = 0
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsAnd: 3
Stats: state = 1
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 1
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 1
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
Stats: state = 2
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 2
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 2
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
Stats: state = 3
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 3
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 3
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
StatsGroupBy: hostgroup_name
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        tic = time.clock()
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        tac = time.clock()
        print "livestatus duration %f" % (tac - tic)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))

        # Again, without Filter:
        request = """GET servicesbyhostgroup
Stats: has_been_checked = 0
Stats: state = 0
Stats: has_been_checked != 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 4
Stats: state = 0
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsAnd: 3
Stats: state = 1
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 1
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 1
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
Stats: state = 2
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 2
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 2
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
Stats: state = 3
Stats: acknowledged = 0
Stats: host_acknowledged = 0
Stats: scheduled_downtime_depth = 0
Stats: host_scheduled_downtime_depth = 0
StatsAnd: 5
Stats: state = 3
Stats: acknowledged = 1
Stats: host_acknowledged = 1
StatsOr: 2
StatsAnd: 2
Stats: state = 3
Stats: scheduled_downtime_depth > 0
Stats: host_scheduled_downtime_depth > 0
StatsOr: 2
StatsAnd: 2
StatsGroupBy: hostgroup_name
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))


    def test_childs(self):
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hosts
Columns: childs
Filter: name = test_host_0
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))
        request = """GET hosts
Columns: childs
Filter: name = test_router_0
OutputFormat: csv
KeepAlive: on
ResponseHeader: fixed16
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        if self.nagios_installed():
            nagresponse = self.ask_nagios(request)
            print "nagresponse----------------------------------------------"
            print nagresponse
            self.assert_(self.lines_equal(response, nagresponse))


    def test_thruk_servicegroup(self):
        self.print_header()
        now = time.time()
        self.update_broker()
        #---------------------------------------------------------------
        # get services of a certain servicegroup
        # test_host_0/test_ok_0 is in 
        #   servicegroup_01,ok via service.servicegroups
        #   servicegroup_02 via servicegroup.members
        #---------------------------------------------------------------
        request = """GET services
Columns: host_name service_description
Filter: groups >= servicegroup_01
OutputFormat: csv
ResponseHeader: fixed16
"""
        # 400 services => 400 lines + header + empty last line
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(len(response.split("\n")) == 402)

        request = """GET servicegroups
Columns: name members
Filter: name = servicegroup_01
OutputFormat: csv
"""
        # 400 services => 400 lines
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        # take first line, take members column, count list elements = 400 services
        self.assert_(len(((response.split("\n")[0]).split(';')[1]).split(',')) == 400)


    def test_sorted_limit(self):
        self.print_header()
        if self.nagios_installed():
            self.start_nagios('5r_100h_2000s')
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        # now send the list of services to the broker in an unordered way
        sched_unsorted = '\n'.join(["%s;%s;%d" % (s.host_name, s.service_description, s.state_id) for s in self.sched.services])

        self.update_broker()
        live_sorted = '\n'.join(["%s;%s;%d" % (s.host_name, s.service_description, s.state_id) for s in self.livestatus_broker.services.values()])

        # Unsorted in the scheduler, sorted in livestatus
        self.assert_(sched_unsorted != live_sorted)
        sched_live_sorted = '\n'.join(sorted(sched_unsorted.split('\n'))) + '\n'
        sched_live_sorted = sched_live_sorted.strip()
        print "first of sched\n(%s)\n--------------\n" % sched_unsorted[:100]
        print "first of live \n(%s)\n--------------\n" % live_sorted[:100]
        print "first of sssed \n(%s)\n--------------\n" % sched_live_sorted[:100]
        print "last of sched\n(%s)\n--------------\n" % sched_unsorted[-100:]
        print "last of live \n(%s)\n--------------\n" % live_sorted[-100:]
        print "last of sssed \n(%s)\n--------------\n" % sched_live_sorted[-100:]
        # But sorted they are the same. 
        self.assert_('\n'.join(sorted(sched_unsorted.split('\n'))) == live_sorted)
  
        svc1 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_00")
        print svc1
        svc2 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_15")
        print svc2
        svc3 = self.sched.services.find_srv_by_name_and_hostname("test_host_005", "test_ok_16")
        print svc3
        svc4 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_05")
        print svc4
        svc5 = self.sched.services.find_srv_by_name_and_hostname("test_host_007", "test_ok_11")
        svc6 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_01")
        svc7 = self.sched.services.find_srv_by_name_and_hostname("test_host_025", "test_ok_03")
        self.scheduler_loop(1, [[svc1, 1, 'W'], [svc2, 1, 'W'], [svc3, 1, 'W'], [svc4, 2, 'C'], [svc5, 3, 'U'], [svc6, 2, 'C'], [svc7, 2, 'C']])
        self.update_broker()
        # 1993O, 3xW, 3xC, 1xU

        # Get all bad services from livestatus
        request = """GET services
Columns: host_name service_description state
ColumnHeaders: off
OutputFormat: csv
Filter: state != 0"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        # Get all bad services from the scheduler
        sched_bad_unsorted = '\n'.join(["%s;%s;%d" % (s.host_name, s.service_description, s.state_id) for s in self.sched.services if s.state_id != 0])
        # Check if the result of the query is sorted
        self.assert_('\n'.join(sorted(sched_bad_unsorted.split('\n'))) == response.strip())

        # Now get the first 3 bad services from livestatus
        request = """GET services
Limit: 3
Columns: host_name service_description state
ColumnHeaders: off
OutputFormat: csv
Filter: state != 0"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print 'query_6_______________\n%s\n%s\n' % (request, response)

        # Now compare the first 3 bad services with the scheduler data
        self.assert_('\n'.join(sorted(sched_bad_unsorted.split('\n'))[:3]) == response.strip())

        # Now check if all services are sorted when queried with a livestatus request
        request = """GET services
Columns: host_name service_description state
ColumnHeaders: off
OutputFormat: csv"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        # Again, get all bad services from the scheduler
        sched_bad_unsorted = '\n'.join(["%s;%s;%d" % (s.host_name, s.service_description, s.state_id) for s in self.sched.services])
        # Check if the result of the query is sorted
        self.assert_('\n'.join(sorted(sched_bad_unsorted.split('\n'))) == response.strip())



class TestConfigComplex(TestConfig):
    def setUp(self):
        self.setup_with_file('etc/nagios_problem_impact.cfg')
        self.testid = str(os.getpid() + random.randint(1, 1000))
        self.livelogs = 'tmp/livelogs.db' + self.testid
        self.pnp4nagios = 'tmp/pnp4nagios_test' + self.testid
        self.livestatus_broker = Livestatus_broker(modconf, '127.0.0.1', str(50000 + os.getpid()), 'live', [], self.livelogs, 365, self.pnp4nagios)
        self.livestatus_broker.create_queues()
        self.livestatus_broker.init()
        print "Cleaning old broks?"
        self.sched.fill_initial_broks()
        self.update_broker()
        self.nagios_path = None
        self.livestatus_path = None
        self.nagios_config = None


    def tearDown(self):
        self.stop_nagios()
        self.livestatus_broker.dbconn.commit()
        self.livestatus_broker.dbconn.close()
        if os.path.exists(self.livelogs):
            os.remove(self.livelogs)
        if os.path.exists(self.pnp4nagios):
            shutil.rmtree(self.pnp4nagios)
        to_del = [attr for attr in self.livestatus_broker.livestatus.__class__.out_map['Host'].keys() if attr.startswith('host_')]
        for attr in to_del:
            del self.livestatus_broker.livestatus.__class__.out_map['Host'][attr]
        self.livestatus_broker = None


    #  test_host_0  has parents test_router_0,test_router_1
    def test_thruk_parents(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hosts
Columns: host_name parents childs
OutputFormat: csv
"""
        good_response = """test_router_0;;test_host_0,test_host_1
test_router_1;;test_host_0,test_host_1
test_host_0;test_router_0,test_router_1;
test_host_1;test_router_0,test_router_1;
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        self.assert_(self.lines_equal(response, good_response))



if __name__ == '__main__':
    #import cProfile
    command = """unittest.main()"""
    unittest.main()
    #cProfile.runctx( command, globals(), locals(), filename="/tmp/livestatus.profile" )

