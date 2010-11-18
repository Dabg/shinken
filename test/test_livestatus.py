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
# This file is used to test host- and service-downtimes.
#

from shinken_test import *

sys.path.append("../shinken/modules/livestatus_broker")
from livestatus_broker import Livestatus_broker
sys.setcheckinterval(10000)

class TestConfig(ShinkenTest):
    def setUp(self):
        self.setup_with_file('etc/nagios_1r_1h_1s.cfg')
        self.livestatus_broker = Livestatus_broker('livestatus', '127.0.0.1', '50000', 'live', '/tmp/livelogs.db')
        self.livestatus_broker.properties = {
            'to_queue' : 0,
            'from_queue' : 0

            }
        self.livestatus_broker.init()
        print "Cleaning old broks?"
        self.sched.fill_initial_broks()
        self.update_broker()


    def update_broker(self):
        #The brok should be manage in the good order
        ids = self.sched.broks.keys()
        ids.sort()
        for brok_id in ids:
            brok = self.sched.broks[brok_id]
            #print "Managing a brok type", brok.type, "of id", brok_id
            #if brok.type == 'update_service_status':
            #    print "Problem?", brok.data['is_problem']
            self.livestatus_broker.manage_brok(brok)
        self.sched.broks = {}


    def lines_equal(self, text1, text2):
        # gets two multiline strings and compares the contents
        # lifestatus output may not be in alphabetical order, so this
        # function is used to compare unordered output with unordered
        # expected output
        sorted1 = "\n".join(sorted(text1.split("\n")))
        sorted2 = "\n".join(sorted(text2.split("\n")))
        return sorted1 == sorted2


    def show_broks(self, title):
        print
        print "--- ", title
        for brok in sorted(self.sched.broks.values(), lambda x, y: x.id - y.id):
            if re.compile('^service_').match(brok.type):
                print "BROK:", brok.type
                print "BROK   ", brok.data['in_checking']
        self.update_broker()
        data = 'GET services\nColumns: service_description is_executing\n'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response


    def test_status(self):
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
        #---------------------------------------------------------------
        # get the full hosts table
        #---------------------------------------------------------------
        data = 'GET hosts'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        #---------------------------------------------------------------
        # get only the host names and addresses
        #---------------------------------------------------------------
        data = 'GET hosts\nColumns: name address hostgroups\nColumnHeaders: on'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        #---------------------------------------------------------------
        # query_1
        #---------------------------------------------------------------
        data = 'GET contacts'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_1_______________\n%s\n%s\n' % (data, response)

        #---------------------------------------------------------------
        # query_2
        #---------------------------------------------------------------
        data = 'GET contacts\nColumns: name alias'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_2_______________\n%s\n%s\n' % (data, response)

        #---------------------------------------------------------------
        # query_3
        #---------------------------------------------------------------
        #self.scheduler_loop(3, svc, 2, 'BAD')
        data = 'GET services\nColumns: host_name description state\nFilter: state = 2\nColumnHeaders: on'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_3_______________\n%s\n%s\n' % (data, response)
        self.assert_(response == 'host_name;description;state\ntest_host_0;test_ok_0;2\n')
        data = 'GET services\nColumns: host_name description state\nFilter: state = 2'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_3_______________\n%s\n%s\n' % (data, response)
        self.assert_(response == 'test_host_0;test_ok_0;2\n')
        data = 'GET services\nColumns: host_name description state\nFilter: state = 0'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_3_______________\n%s\n%s\n' % (data, response)
        self.assert_(response == '\n')
        duration = 180
        now = time.time()
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_ok_0;%d;%d;0;0;%d;lausser;blablub" % (now, now, now + duration, duration)
        self.sched.run_external_command(cmd)
        self.update_broker()
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        self.update_broker()
        self.scheduler_loop(3, [[svc, 2, 'BAD']])
        self.update_broker()
        data = 'GET services\nColumns: host_name description scheduled_downtime_depth\nFilter: state = 2\nFilter: scheduled_downtime_depth = 1'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_3_______________\n%s\n%s\n' % (data, response)
        self.assert_(response == 'test_host_0;test_ok_0;1\n')

        #---------------------------------------------------------------
        # query_4
        #---------------------------------------------------------------
        data = 'GET services\nColumns: host_name description state\nFilter: state = 2\nFilter: in_notification_period = 1\nAnd: 2\nFilter: state = 0\nOr: 2\nFilter: host_name = test_host_0\nFilter: description = test_ok_0\nAnd: 3\nFilter: contacts >= harri\nFilter: contacts >= test_contact\nOr: 3'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_4_______________\n%s\n%s\n' % (data, response)
        self.assert_(response == 'test_host_0;test_ok_0;2\n')

        #---------------------------------------------------------------
        # query_6
        #---------------------------------------------------------------
        data = 'GET services\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_6_______________\n%s\n%s\n' % (data, response)
        self.assert_(response == '0;0;1;0\n')

        #---------------------------------------------------------------
        # query_7
        #---------------------------------------------------------------
        data = 'GET services\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\nFilter: contacts >= test_contact'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'query_6_______________\n%s\n%s\n' % (data, response)
        self.assert_(response == '0;0;1;0\n')


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
        data = 'GET services\nColumns: host_name description state\nOutputFormat: json'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'json wo headers__________\n%s\n%s\n' % (data, response)
        self.assert_(response == '[["test_host_0","test_ok_0",2]]\n')
        data = 'GET services\nColumns: host_name description state\nOutputFormat: json\nColumnHeaders: on'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print 'json with headers__________\n%s\n%s\n' % (data, response)
        self.assert_(response == '[["host_name","description","state"],["test_host_0","test_ok_0",2]]\n')
        #100% mklivesttaus: self.assert_(response == '[["host_name","description","state"],\n["test_host_0","test_ok_0",2]]\n')


    def test_thruk(self):
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
        #---------------------------------------------------------------
        # get the full hosts table
        #---------------------------------------------------------------
        data = 'GET status\nColumns: livestatus_version program_version accept_passive_host_checks accept_passive_service_checks check_external_commands check_host_freshness check_service_freshness enable_event_handlers enable_flap_detection enable_notifications execute_host_checks execute_service_checks last_command_check last_log_rotation nagios_pid obsess_over_hosts obsess_over_services process_performance_data program_start interval_length'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET hosts
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
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET comments
Columns: host_name source type author comment entry_time entry_type expire_time
Filter: service_description ="""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET hosts
Columns: comments has_been_checked state name address acknowledged notifications_enabled active_checks_enabled is_flapping scheduled_downtime_depth is_executing notes_url_expanded action_url_expanded icon_image_expanded icon_image_alt last_check last_state_change plugin_output next_check long_plugin_output
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        duration = 180
        now = time.time()
        cmd = "[%lu] SCHEDULE_SVC_DOWNTIME;test_host_0;test_warning_00;%d;%d;0;0;%d;lausser;blablubsvc" % (now, now, now + duration, duration)
        print cmd
        self.sched.run_external_command(cmd)
        cmd = "[%lu] SCHEDULE_HOST_DOWNTIME;test_host_0;%d;%d;0;0;%d;lausser;blablubhost" % (now, now, now + duration, duration)
        print cmd
        self.sched.run_external_command(cmd)
        self.update_broker()
        self.scheduler_loop(1, [[svc, 0, 'OK']])
        self.update_broker()
        self.scheduler_loop(3, [[svc, 2, 'BAD']])
        self.update_broker()
        data = """GET downtimes
Filter: service_description =
Columns: author comment end_time entry_time fixed host_name id start_time
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        data = """GET comments
Filter: service_description =
Columns: author comment
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET services
Filter: has_been_checked = 1
Filter: check_type = 0
Stats: sum has_been_checked
Stats: sum latency
Separators: 10 59 44 124
ResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET services
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
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET services\nFilter: has_been_checked = 1\nFilter: check_type = 0\nStats: sum has_been_checked as has_been_checked\nStats: sum latency as latency_sum\nStats: sum execution_time as execution_time_sum\nStats: min latency as latency_min\nStats: min execution_time as execution_time_min\nStats: max latency as latency_max\nStats: max execution_time as execution_time_max\n\nResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET hostgroups\nColumnHeaders: on\nResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET hosts\nColumns: name groups\nColumnHeaders: on\nResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET hostgroups\nColumns: name num_services num_services_ok\nColumnHeaders: on\nResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        data = """GET hostgroups\nColumns: name num_services_pending num_services_ok num_services_warning num_services_critical num_services_unknown worst_service_state worst_service_hard_state\nColumnHeaders: on\nResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 0, 'OK']])
        self.update_broker()
        self.scheduler_loop(1, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()

        print "WARNING SOFT;1"
        # worst_service_state 1, worst_service_hard_state 0
        data = """GET hostgroups\nColumns: name num_services_pending num_services_ok num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nColumnHeaders: on\nResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        self.scheduler_loop(3, [[host, 0, 'UP'], [router, 0, 'UP'], [svc, 1, 'WARNING']])
        self.update_broker()
        print "WARNING HARD;3"
        # worst_service_state 1, worst_service_hard_state 1
        data = """GET hostgroups\nColumns: name num_services_pending num_services_ok num_services_warn num_services_crit num_services_unknown worst_service_state worst_service_hard_state\nColumnHeaders: on\nResponseHeader: fixed16"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        for s in self.livestatus_broker.livestatus.services.values():
            print "%s %d %s;%d" % (s.state, s.state_id, s.state_type, s.attempt)


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

        #data = """GET comments\nColumns: host_name service_description id source type author comment entry_time entry_type persistent expire_time expires\nFilter: service_description !=\nResponseHeader: fixed16\nOutputFormat: json\n"""
        data = """GET services\nColumns: comments host_comments host_is_executing is_executing\nFilter: service_description !=\nResponseHeader: fixed16\nOutputFormat: json\n"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        good_response = """200          17
[[[""" + svc_comment_list +"""],[],0,0]]
"""
        self.assert_(response == good_response) # json

        data = """GET services\nColumns: comments host_comments host_is_executing is_executing\nFilter: service_description !=\nResponseHeader: fixed16\n"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        good_response = """200           9
""" + svc_comment_list + """;;0;0
"""
        self.assert_(response == good_response) # csv


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
        data = """GET log
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

        response = self.livestatus_broker.livestatus.handle_request(data)
        print response

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

        data = """GET log
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

        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = """GET log
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
        data = """GET log
Columns: time type options state current_host_name
Filter: time >= """ + str(int(start)) + """
Filter: time <= """ + str(int(end)) + """
Filter: current_host_name = test_host_0
Filter: current_service_description = test_ok_0
And: 2"""

        response = self.livestatus_broker.livestatus.handle_request(data)
        print response


    def test_thruk_tac_svc(self):
        self.print_header()
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
        data = """GET services
Filter: has_been_checked = 1
Filter: check_type = 0
Stats: sum has_been_checked
Stats: sum latency
Stats: sum execution_time
Stats: min latency
Stats: min execution_time
Stats: max latency
Stats: max execution_time"""

        response = self.livestatus_broker.livestatus.handle_request(data)
        print response


    def test_columns(self):
        self.print_header()
        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        data = """GET columns"""
        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = """GET schedulers"""
        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = """GET schedulers"""
        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = """GET reactionners"""
        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = """GET reactionners"""
        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = """GET pollers"""
        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = """GET pollers"""
        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = """GET brokers"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        good_response = """address;alive;name;port;spare
localhost;1;broker-1;7772;0
othernode;1;broker-2;7772;1
"""
        print response == good_response
        self.assert_(response == good_response)

        #Now the update part
        pol.alive = False
        b2 = pol.get_initial_status_brok()
        self.sched.add(b2)

        self.update_broker()
        #---------------------------------------------------------------
        # get the columns meta-table
        #---------------------------------------------------------------
        data = """GET brokers"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        good_response = """address;alive;name;port;spare
localhost;1;broker-1;7772;0
othernode;0;broker-2;7772;1
"""
        print response == good_response
        self.assert_(response == good_response)



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
        data = """GET problems"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        print "FUCK", response
        good_response = """impacts;source
test_host_0,test_host_0/test_ok_0;test_router_0
"""
        print response == good_response
        self.assert_(response == good_response)



    def test_limit(self):
        self.print_header() 
        now = time.time()
        self.update_broker()
        #---------------------------------------------------------------
        # get the full hosts table
        #---------------------------------------------------------------
        data = 'GET hosts\nColumns: host_name\n'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        good_response = """test_host_0
test_router_0
"""
        self.assert_(self.lines_equal(response, good_response))

        data = 'GET hosts\nColumns: host_name\nLimit: 1\n'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        good_response = """test_host_0
"""
        # it must be test_host_0 because with Limit: the output is 
        # alphabetically ordered
        self.assert_(response == good_response)



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
        data = 'GET hosts\nColumns: host_name is_impact source_problems\n'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print "moncul", response
        #good_response = """test_host_0
#test_router_0
#"""
        #self.assert_(self.lines_equal(response, good_response))

        print "Now got impact"
        data = 'GET hosts\nColumns: host_name is_problem impacts\n'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print "moncul", response
        good_response = """test_host_0
test_router_0
"""
#        self.assert_(self.lines_equal(response, good_response))

        data = 'GET hosts\nColumns: host_name\nLimit: 1\n'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        good_response = """test_host_0
"""
        # it must be test_host_0 because with Limit: the output is 
        # alphabetically ordered
#        self.assert_(response == good_response)



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
        data = """GET services
Columns: host_name service_description
Filter: groups >= servicegroup_01
OutputFormat: csv
ResponseHeader: fixed16
"""
        response = self.livestatus_broker.livestatus.handle_request(data)
        self.assert_(response == """200          22
test_host_0;test_ok_0
""")
        data = """GET services
Columns: host_name service_description
Filter: groups >= servicegroup_02
OutputFormat: csv
ResponseHeader: fixed16
"""
        response = self.livestatus_broker.livestatus.handle_request(data)
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
        data = 'GET services\nColumns: service_description is_executing\n'
        response = self.livestatus_broker.livestatus.handle_request(data)
        print response
        


if __name__ == '__main__':
    #import cProfile
    command = """unittest.main()"""
    unittest.main()
    #cProfile.runctx( command, globals(), locals(), filename="Thruk.profile" )

