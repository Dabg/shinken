#!/usr/bin/env python
#Copyright (C) 2009-2010 :
#    Gabes Jean, naparuba@gmail.com
#    Gerhard Lausser, Gerhard.Lausser@consol.de
#    Gregory Starck, g.starck@gmail.com
#    Hartmut Goebel, h.goebel@goebel-consult.de
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


""" This is the main class for the Host. In fact it's mainly
about the configuration part. for the running one, it's better
to look at the schedulingitem class that manage all
scheduling/consome check smart things :)
"""

import time

from item import Items
from schedulingitem import SchedulingItem

from shinken.autoslots import AutoSlots
from shinken.util import format_t_into_dhms_format, to_hostnames_list, get_obj_name, to_svc_hst_distinct_lists, to_list_string_of_names
from shinken.property import BoolProp, IntegerProp, FloatProp, CharProp, StringProp, ListProp
from shinken.graph import Graph
from shinken.macroresolver import MacroResolver
from shinken.eventhandler import EventHandler
from shinken.log import logger


class Host(SchedulingItem):
    #AutoSlots create the __slots__ with properties and
    #running_properties names
    __metaclass__ = AutoSlots

    id = 1 #0 is reserved for host (primary node for parents)
    ok_up = 'UP'
    my_type = 'host'


    # properties defined by configuration
    # *required : is required in conf
    # *default : default value if no set in conf
    # *pythonize : function to call when transfort string to python object
    # *fill_brok : if set, send to broker. there are two categories: full_status for initial and update status, check_result for check results
    # *no_slots : do not take this property for __slots__
    #  Only for the inital call
    # conf_send_preparation : if set, will pass the property to this function. It's used to "flatten"
    #  some dangerous properties like realms that are too 'linked' to be send like that.
    # brok_transformation : if set, will call the function with the value of the property
    #  the major times it will be to flatten the data (like realm_name instead of the realm object).
    properties = SchedulingItem.properties.copy()
    properties.update({
        'host_name':            StringProp(fill_brok=['full_status', 'check_result', 'next_schedule']),
        'alias':                StringProp(fill_brok=['full_status']),
        'display_name':         StringProp(default='none', fill_brok=['full_status']),
        'address':              StringProp(fill_brok=['full_status']),
        'parents':              ListProp(brok_transformation=to_hostnames_list, default='', fill_brok=['full_status']),
        'hostgroups':           StringProp(brok_transformation=to_list_string_of_names, default='', fill_brok=['full_status']),
        'check_command':        StringProp(default='_internal_host_up', fill_brok=['full_status']),
        'initial_state':        CharProp(default='u', fill_brok=['full_status']),
        'max_check_attempts':   IntegerProp(fill_brok=['full_status']),
        'check_interval':       IntegerProp(default='0', fill_brok=['full_status']),
        'retry_interval':       IntegerProp(default='0', fill_brok=['full_status']),
        'active_checks_enabled': BoolProp(default='1', fill_brok=['full_status'], retention=True),
        'passive_checks_enabled': BoolProp(default='1', fill_brok=['full_status'], retention=True),
        'check_period':         StringProp(fill_brok=['full_status']),
        'obsess_over_host':     BoolProp(default='0', fill_brok=['full_status'], retention=True),
        'check_freshness':      BoolProp(default='0', fill_brok=['full_status'], retention=True),
        'freshness_threshold':  IntegerProp(default='0', fill_brok=['full_status']),
        'event_handler':        StringProp(default='', fill_brok=['full_status']),
        'event_handler_enabled': BoolProp(default='0', fill_brok=['full_status']),
        'low_flap_threshold':   IntegerProp(default='25', fill_brok=['full_status']),
        'high_flap_threshold':  IntegerProp(default='50', fill_brok=['full_status']),
        'flap_detection_enabled': BoolProp(default='1', fill_brok=['full_status'], retention=True),
        'flap_detection_options': ListProp(default='o,d,u', fill_brok=['full_status']),
        'process_perf_data':    BoolProp(default='1', fill_brok=['full_status'], retention=True),
        'retain_status_information': BoolProp(default='1', fill_brok=['full_status']),
        'retain_nonstatus_information': BoolProp(default='1', fill_brok=['full_status']),
        'contacts':             StringProp(default='', fill_brok=['full_status']),
        'contact_groups':       StringProp(default='', fill_brok=['full_status']),
        'notification_interval': IntegerProp(default='60', fill_brok=['full_status']),
        'first_notification_delay': IntegerProp(default='0', fill_brok=['full_status']),
        'notification_period':  StringProp(fill_brok=['full_status']),
        'notification_options': ListProp(default='d,u,r,f', fill_brok=['full_status']),
        'notifications_enabled': BoolProp(default='1', fill_brok=['full_status']),
        'stalking_options':     ListProp(default='', fill_brok=['full_status']),
        'notes':                StringProp(default='', fill_brok=['full_status']),
        'notes_url':            StringProp(default='', fill_brok=['full_status']),
        'action_url':           StringProp(default='', fill_brok=['full_status']),
        'icon_image':           StringProp(default='', fill_brok=['full_status']),
        'icon_image_alt':       StringProp(default='', fill_brok=['full_status']),
        'vrml_image':           StringProp(default='', fill_brok=['full_status']),
        'statusmap_image':      StringProp(default='', fill_brok=['full_status']),

        # No slots for this 2 because begin property by a number seems bad
        # it's stupid!
        '2d_coords':            StringProp(default='', fill_brok=['full_status'], no_slots=True),
        '3d_coords':            StringProp(default='', fill_brok=['full_status'], no_slots=True),
        'failure_prediction_enabled': BoolProp(default='0', fill_brok=['full_status']),

        ### New to shinken
        # 'fill_brok' is ok because in scheduler it's already
        # a string from conf_send_preparation
        'realm':                StringProp(default=None, fill_brok=['full_status'], conf_send_preparation=get_obj_name),
        'poller_tag':           StringProp(default='None'),
        'reactionner_tag':           StringProp(default='None'),
        'resultmodulations':    StringProp(default=''),
        'criticitymodulations': StringProp(default=''),
        'escalations':          StringProp(default='', fill_brok=['full_status']),
        'maintenance_period':   StringProp(default='', fill_brok=['full_status']),

        # Criticity value
        'criticity':            IntegerProp(default='2', fill_brok=['full_status']),
    })

    # properties set only for running purpose
    # retention : save/load this property from retention
    running_properties = SchedulingItem.running_properties.copy()
    running_properties.update({
        'last_chk':             IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'next_chk':             IntegerProp(default=0, fill_brok=['full_status', 'next_schedule'], retention=True),
        'in_checking':          BoolProp(default=False, fill_brok=['full_status', 'check_result', 'next_schedule']),
        'latency':              FloatProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'attempt':              IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'state':                StringProp(default='PENDING', fill_brok=['full_status'], retention=True),
        'state_id':             IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'state_type':           StringProp(default='HARD', fill_brok=['full_status'], retention=True),
        'state_type_id':        IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'current_event_id':     StringProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_event_id':        IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_state':           StringProp(default='PENDING', fill_brok=['full_status'], retention=True),
        'last_state_id':        IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'last_state_type' :     StringProp(default='HARD', fill_brok=['full_status'],  retention=True),
        'last_state_change':    FloatProp(default=time.time(), fill_brok=['full_status'], retention=True),
        'last_hard_state_change': FloatProp(default=time.time(), fill_brok=['full_status', 'check_result'], retention=True),
        'last_hard_state':      StringProp(default='PENDING', fill_brok=['full_status'], retention=True),
        'last_hard_state_id' :  IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'last_time_up':         IntegerProp(default=int(time.time()), fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_down':       IntegerProp(default=int(time.time()), fill_brok=['full_status', 'check_result'], retention=True),
        'last_time_unreachable': IntegerProp(default=int(time.time()), fill_brok=['full_status', 'check_result'], retention=True),
        'duration_sec':         IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'output':               StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'long_output':          StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'is_flapping':          BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'flapping_comment_id':  IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        # No broks for _depend_of because of to much links to hosts/services
        # dependencies for actions like notif of event handler, so AFTER check return
        'act_depend_of':        StringProp(default=[]),

        # dependencies for checks raise, so BEFORE checks
        'chk_depend_of':        StringProp(default=[]),

        # elements that depend of me, so the reverse than just uppper
        'act_depend_of_me':     StringProp(default=[]),

        # elements that depend of me
        'chk_depend_of_me':     StringProp(default=[]),
        'last_state_update':    StringProp(default=time.time(), fill_brok=['full_status'], retention=True),

        # no brok ,to much links
        'services':             StringProp(default=[]),

        # No broks, it's just internal, and checks have too links
        'checks_in_progress':   StringProp(default=[]),

        # No broks, it's just internal, and checks have too links
        'notifications_in_progress': StringProp(default={}, retention=True),
        'downtimes':            StringProp(default=[], fill_brok=['full_status'], retention=True),
        'comments':             StringProp(default=[], fill_brok=['full_status'], retention=True),
        'flapping_changes':     StringProp(default=[], fill_brok=['full_status'], retention=True),
        'percent_state_change': FloatProp(default=0.0, fill_brok=['full_status', 'check_result'], retention=True),
        'problem_has_been_acknowledged': BoolProp(default=False, fill_brok=['full_status'], retention=True),
        'acknowledgement':      StringProp(default=None, retention=True),
        'acknowledgement_type': IntegerProp(default=1, fill_brok=['full_status', 'check_result'], retention=True),
        'check_type':           IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'has_been_checked':     IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'should_be_scheduled':  IntegerProp(default=1, fill_brok=['full_status'], retention=True),
        'last_problem_id':      IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'current_problem_id':   IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'execution_time':       FloatProp(default=0.0, fill_brok=['full_status', 'check_result'], retention=True),
        'last_notification':    FloatProp(default=time.time(), fill_brok=['full_status'], retention=True),
        'current_notification_number': IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'current_notification_id': IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'check_flapping_recovery_notification': BoolProp(default=True, fill_brok=['full_status'], retention=True),
        'scheduled_downtime_depth': IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'pending_flex_downtime': IntegerProp(default=0, fill_brok=['full_status'], retention=True),
        'timeout':              IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'start_time':           IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'end_time':             IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'early_timeout':        IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'return_code':          IntegerProp(default=0, fill_brok=['full_status', 'check_result'], retention=True),
        'perf_data':            StringProp(default='', fill_brok=['full_status', 'check_result'], retention=True),
        'last_perf_data':       StringProp(default='', retention=True),
        'customs':              StringProp(default={}, fill_brok=['full_status']),
        'got_default_realm' :   BoolProp(default=False),

        # use for having all contacts we have notified
        'notified_contacts':    StringProp(default=set()),

        'in_scheduled_downtime': BoolProp(default=False, retention=True),
        'in_scheduled_downtime_during_last_check': BoolProp(default=False, retention=True),

        # put here checks and notif raised
        'actions':              StringProp(default=[]),
        # and here broks raised
        'broks':                StringProp(default=[]),

        # For knowing with which elements we are in relation
        # of dep.
        # childs are the hosts that have US as parent, so
        # only a network dep
        'childs':               StringProp(brok_transformation=to_hostnames_list, default=[], fill_brok=['full_status']),
        # Here it's the elements we are depending on
        # so our parents as network relation, or a host
        # we are depending in a hostdependency
        # or even if we are businesss based.
        'parent_dependencies' : StringProp(brok_transformation=to_svc_hst_distinct_lists, default=set(), fill_brok=['full_status']),
        # Here it's the guys taht depend on us. So it's the total
        # oposite of the parent_dependencies 
        'child_dependencies':   StringProp(
            brok_transformation=to_svc_hst_distinct_lists,
            default=set(),
            fill_brok=['full_status']),


        ### Problem/impact part
        'is_problem':           StringProp(default=False, fill_brok=['full_status']),
        'is_impact':            StringProp(default=False, fill_brok=['full_status']),

        # the save value of our criticity for "problems"
        'my_own_criticity':     IntegerProp(default=-1),

        # list of problems that make us an impact
        'source_problems':      StringProp(brok_transformation=to_svc_hst_distinct_lists, default=[], fill_brok=['full_status']),

        # list of the impact I'm the cause of
        'impacts':              StringProp(brok_transformation=to_svc_hst_distinct_lists, default=[], fill_brok=['full_status']),

        # keep a trace of the old state before being an impact
        'state_before_impact':  StringProp(default='PENDING'),
        # keep a trace of the old state id before being an impact
        'state_id_before_impact': StringProp(default=0),
        # if the state change, we know so we do not revert it
        'state_changed_since_impact': StringProp(default=False),

        #BUSINESS CORRELATOR PART
        # Say if we are business based rule or not
        'got_business_rule' : BoolProp(default=False, fill_brok=['full_status']),
        # Our Dependency node for the business rule
        'business_rule' : StringProp(default=None),
        
        # Manage the unkown/unreach during hard state
        # From now its not really used
        'in_hard_unknown_reach_phase' : BoolProp(default=False, retention=True),
        'was_in_hard_unknown_reach_phase' : BoolProp(default=False, retention=True),
        'state_before_hard_unknown_reach_phase' : StringProp(default='UP', retention=True),

    })

    # Hosts macros and prop that give the information
    # the prop can be callable or not
    macros = {
        'HOSTNAME':          'host_name',
        'HOSTDISPLAYNAME':   'display_name',
        'HOSTALIAS':         'alias',
        'HOSTADDRESS':       'address',
        'HOSTSTATE':         'state',
        'HOSTSTATEID':       'state_id',
        'LASTHOSTSTATE':     'last_state',
        'LASTHOSTSTATEID':   'last_state_id',
        'HOSTSTATETYPE':     'state_type',
        'HOSTATTEMPT':       'attempt',
        'MAXHOSTATTEMPTS':   'max_check_attempts',
        'HOSTEVENTID':       'current_event_id',
        'LASTHOSTEVENTID':   'last_event_id',
        'HOSTPROBLEMID':     'current_problem_id',
        'LASTHOSTPROBLEMID': 'last_problem_id',
        'HOSTLATENCY':       'latency',
        'HOSTEXECUTIONTIME': 'execution_time',
        'HOSTDURATION':      'get_duration',
        'HOSTDURATIONSEC':   'get_duration_sec',
        'HOSTDOWNTIME':      'get_downtime',
        'HOSTPERCENTCHANGE': 'percent_state_change',
        'HOSTGROUPNAME':     'get_groupname',
        'HOSTGROUPNAMES':    'get_groupnames',
        'LASTHOSTCHECK':     'last_chk',
        'LASTHOSTSTATECHANGE': 'last_state_change',
        'LASTHOSTUP':        'last_time_up',
        'LASTHOSTDOWN':      'last_time_down',
        'LASTHOSTUNREACHABLE': 'last_time_unreachable',
        'HOSTOUTPUT':        'output',
        'LONGHOSTOUTPUT':    'long_output',
        'HOSTPERFDATA':      'perf_data',
        'LASTHOSTPERFDATA':  'last_perf_data',
        'HOSTCHECKCOMMAND':  'get_check_command',
        'HOSTACKAUTHOR':     'get_ack_author_name',
        'HOSTACKAUTHORNAME': 'get_ack_author_name',
        'HOSTACKAUTHORALIAS': 'get_ack_author_name',
        'HOSTACKCOMMENT':    'get_ack_comment',
        'HOSTACTIONURL':     'action_url',
        'HOSTNOTESURL':      'notes_url',
        'HOSTNOTES':         'notes',
        'TOTALHOSTSERVICES': 'get_total_services',
        'TOTALHOSTSERVICESOK': 'get_total_services_ok',
        'TOTALHOSTSERVICESWARNING': 'get_total_services_warning',
        'TOTALHOSTSERVICESUNKNOWN': 'get_total_services_unknown',
        'TOTALHOSTSERVICESCRITICAL': 'get_total_services_critical'
    }


    # This tab is used to transform old parameters name into new ones
    # so from Nagios2 format, to Nagios3 ones
    old_properties = {
        'normal_check_interval': 'check_interval',
        'retry_check_interval':  'retry_interval'
    }


####### 
#                   __ _                       _   _             
#                  / _(_)                     | | (_)            
#   ___ ___  _ __ | |_ _  __ _ _   _ _ __ __ _| |_ _  ___  _ __  
#  / __/ _ \| '_ \|  _| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \ 
# | (_| (_) | | | | | | | (_| | |_| | | | (_| | |_| | (_) | | | |
#  \___\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|
#                         __/ |                                  
#                        |___/                                   
######


    # Fill adresse with host_name if not already set
    def fill_predictive_missing_parameters(self):
        if hasattr(self, 'host_name') and not hasattr(self, 'address'):
            self.address = self.host_name
        if hasattr(self, 'host_name') and not hasattr(self, 'alias'):
            self.alias = self.host_name



    # Check is required prop are set:
    # contacts OR contactgroups is need
    def is_correct(self):
        state = True #guilty or not? :)
        cls = self.__class__

        special_properties = ['check_period', 'notification_interval', 'check_period',
                              'notification_period']
        for prop, entry in cls.properties.items():
            if prop not in special_properties:
                if not hasattr(self, prop) and entry.required:
                    logger.log("%s : I do not have %s" % (self.get_name(), prop))
                    state = False #Bad boy...

        # Raised all previously saw errors like unknown contacts and co
        if self.configuration_errors != []:
            state = False
            for err in self.configuration_errors:
                logger.log(err)

        if not hasattr(self, 'notification_period'):
            self.notification_period = None

        # Ok now we manage special cases...
        if self.notifications_enabled and self.contacts == []:
            logger.log("Waring : the host %s do not have contacts nor contact_groups" % self.get_name())
        
        if getattr(self, 'check_command', None) is None:
            logger.log("%s : I've got no check_command" % self.get_name())
            state = False
        # Ok got a command, but maybe it's invalid
        else:
            if not self.check_command.is_valid():
                logger.log("%s : my check_command %s is invalid" % (self.get_name(), self.check_command.command))
                state = False
            if self.got_business_rule:
                if not self.business_rule.is_valid():
                    logger.log("%s : my business rule is invalid" % (self.get_name(),))
                    for bperror in self.business_rule.configuration_errors:
                        logger.log("%s : %s" % (self.get_name(), bperror))
                    state = False
        
        if not hasattr(self, 'notification_interval') and self.notifications_enabled == True:
            logger.log("%s : I've got no notification_interval but I've got notifications enabled" % self.get_name())
            state = False

        # If active check is enabled with a check_interval!=0, we must have a check_period
        if ( getattr(self, 'active_checks_enabled', False) 
             and getattr(self, 'check_period', None) is None 
             and getattr(self, 'check_interval', 1) != 0 ):
            logger.log("%s : My check_period is not correct" % self.get_name())
            state = False
        
        if not hasattr(self, 'check_period'):
            self.check_period = None

        if hasattr(self, 'host_name'):
            for c in cls.illegal_object_name_chars:
                if c in self.host_name:
                    logger.log("%s : My host_name got the caracter %s that is not allowed." % (self.get_name(), c))
                    state = False

        return state


    # Search in my service if I've got the service
    def find_service_by_name(self, service_description):
        for s in self.services:
            if getattr(s, 'service_description', '__UNNAMED_SERVICE__') == service_description:
                return s
        return None


    # For get a nice name
    def get_name(self):
        if not self.is_tpl():
            try:
                return self.host_name
            except AttributeError: # outch, no hostname
                return 'UNNAMEDHOST'
        else:
            try:
                return self.name
            except AttributeError: # outch, no name for this template
                return 'UNNAMEDHOSTTEMPLATE'


    # For debugin purpose only
    def get_dbg_name(self):
        return self.host_name


    # Say if we got the other in one of your dep list
    def is_linked_with_host(self, other):
        for (h, status, type, timeperiod, inherits_parent) in self.act_depend_of:
            if h == other:
                return True
        return False


    # Delete all links in the act_depend_of list of self and other
    def del_host_act_dependancy(self, other):
        to_del = []
        # First we remove in my list
        for (h, status, type, timeperiod, inherits_parent) in self.act_depend_of:
            if h == other:
                to_del.append( (h, status, type, timeperiod, inherits_parent))
        for t in to_del:
            self.act_depend_of.remove(t)

        #And now in the father part
        to_del = []
        for (h, status, type, timeperiod, inherits_parent) in other.act_depend_of_me:
            if h == self:
                to_del.append( (h, status, type, timeperiod, inherits_parent) )
        for t in to_del:
            other.act_depend_of_me.remove(t)
        

    # Add a dependancy for action event handler, notification, etc)
    # and add ourself in it's dep list
    def add_host_act_dependancy(self, h, status, timeperiod, inherits_parent):
        # I add him in MY list
        self.act_depend_of.append( (h, status, 'logic_dep', timeperiod, inherits_parent) )
        # And I add me in it's list
        h.act_depend_of_me.append( (self, status, 'logic_dep', timeperiod, inherits_parent) )

        # And the parent/child dep lists too
        h.register_son_in_parent_child_dependencies(self)


    # Register the dependancy between 2 service for action (notification etc)
    # but based on a BUSINESS rule, so on fact:
    # ERP depend on database, so we fill just database.act_depend_of_me
    # because we will want ERP mails to go on! So call this
    # on the database service with the srv=ERP service
    def add_business_rule_act_dependancy(self, h, status, timeperiod, inherits_parent):
        # first I add the other the I depend on in MY list
        # I only register so he know that I WILL be a inpact
        self.act_depend_of_me.append( (h, status, 'business_dep',
                                      timeperiod, inherits_parent) )

        # And the parent/child dep lists too
        self.register_son_in_parent_child_dependencies(h)


    # Add a dependancy for check (so before launch)
    def add_host_chk_dependancy(self, h, status, timeperiod, inherits_parent):
        # I add him in MY list
        self.chk_depend_of.append( (h, status, 'logic_dep', timeperiod, inherits_parent) )
        # And I add me in it's list
        h.chk_depend_of_me.append( (self, status, 'logic_dep', timeperiod, inherits_parent) )

        # And we fill parent/childs dep for brok purpose
        # Here self depend on h
        h.register_son_in_parent_child_dependencies(self)


    # Add one of our service to services (at linkify)
    def add_service_link(self, service):
        self.services.append(service)



#####
#                         _             
#                        (_)            
#  _ __ _   _ _ __  _ __  _ _ __   __ _ 
# | '__| | | | '_ \| '_ \| | '_ \ / _` |
# | |  | |_| | | | | | | | | | | | (_| |
# |_|   \__,_|_| |_|_| |_|_|_| |_|\__, |
#                                  __/ |
#                                 |___/ 
####



    # Set unreachable : all our parents are down!
    # We have a special state, but state was already set, we just need to
    # update it. We are no DOWN, we are UNREACHABLE and
    # got a state id is 2
    def set_unreachable(self):
        now = time.time()
        self.state_id = 2
        self.state = 'UNREACHABLE'
        self.last_time_unreachable = int(now)


    # We just go an impact, so we go unreachable
    # But only if we enable this stte change in the conf
    def set_impact_state(self):
        cls = self.__class__
        if cls.enable_problem_impacts_states_change:
            # Keep a trace of the old state (problem came back before
            # a new checks)
            self.state_before_impact = self.state
            self.state_id_before_impact = self.state_id
            # This flag will know if we overide the impact state
            self.state_changed_since_impact = False
            self.state = 'UNREACHABLE'#exit code UNDETERMINED
            self.state_id = 2


    # Ok, we are no more an impact, if no news checks
    # overide the impact state, we came back to old
    # states
    # And only if impact state change is set in configuration
    def unset_impact_state(self):
        cls = self.__class__
        if cls.enable_problem_impacts_states_change and not self.state_changed_since_impact:
            self.state = self.state_before_impact
            self.state_id = self.state_id_before_impact


    # set the state in UP, DOWN, or UNDETERMINED
    # with the status of a check. Also update last_state
    def set_state_from_exit_status(self, status):
        now = time.time()
        self.last_state_update = now

        # we should put in last_state the good last state:
        # if not just change the state by an problem/impact
        # we can take current state. But if it's the case, the
        # real old state is self.state_before_impact (it's teh TRUE
        # state in fact)
        # And only if we enable the impact state change
        cls = self.__class__
        if cls.enable_problem_impacts_states_change and self.is_impact and not self.state_changed_since_impact:
            self.last_state = self.state_before_impact
        else:
            self.last_state = self.state

        if status == 0:
            self.state = 'UP'
            self.state_id = 0
            self.last_time_up = int(self.last_state_update)
            state_code = 'u'
        elif status in (1, 2, 3):
            self.state = 'DOWN'
            self.state_id = 1
            self.last_time_down = int(self.last_state_update)
            state_code = 'd'
        else:
            self.state = 'DOWN'#exit code UNDETERMINED
            self.state_id = 1
            self.last_time_down = int(self.last_state_update)
            state_code = 'd'
        if state_code in self.flap_detection_options:
            self.add_flapping_change(self.state != self.last_state)
        if self.state != self.last_state:
            self.last_state_change = self.last_state_update
        self.duration_sec = now - self.last_state_change


    # See if status is status. Can be low of high format (o/UP, d/DOWN, ...)
    def is_state(self, status):
        if status == self.state:
            return True
        # Now low status
        elif status == 'o' and self.state == 'UP':
            return True
        elif status == 'd' and self.state == 'DOWN':
            return True
        elif status == 'u' and self.state == 'UNREACHABLE':
            return True
        return False


    # The last time when the state was not UP
    def last_time_non_ok_or_up(self):
        if self.last_time_down > self.last_time_up:
            last_time_non_up = self.last_time_down
        else:
            last_time_non_up = 0
        return last_time_non_up


    # Add a log entry with a HOST ALERT like:
    # HOST ALERT: server;DOWN;HARD;1;I don't know what to say...
    def raise_alert_log_entry(self):
        logger.log('HOST ALERT: %s;%s;%s;%d;%s' % (self.get_name(), self.state, self.state_type, self.attempt, self.output))


    # If the configuration allow it, raise an initial log like
    # CURRENT HOST STATE: server;DOWN;HARD;1;I don't know what to say...
    def raise_initial_state(self):
        if self.__class__.log_initial_states:
            logger.log('CURRENT HOST STATE: %s;%s;%s;%d;%s' % (self.get_name(), self.state, self.state_type, self.attempt, self.output))


    # Add a log entry with a Freshness alert like:
    # Warning: The results of host 'Server' are stale by 0d 0h 0m 58s (threshold=0d 1h 0m 0s).
    # I'm forcing an immediate check of the host.
    def raise_freshness_log_entry(self, t_stale_by, t_threshold):
        logger.log("Warning: The results of host '%s' are stale by %s (threshold=%s).  I'm forcing an immediate check of the host." \
                      % (self.get_name(), format_t_into_dhms_format(t_stale_by), format_t_into_dhms_format(t_threshold)))


    # Raise a log entry with a Notification alert like
    # HOST NOTIFICATION: superadmin;server;UP;notify-by-rss;no output
    def raise_notification_log_entry(self, n):
        contact = n.contact
        command = n.command_call
        if n.type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'CUSTOM', 'ACKNOWLEDGEMENT', 'FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
            state = '%s (%s)' % (n.type, self.state)
        else:
            state = self.state
        if self.__class__.log_notifications:
            logger.log("HOST NOTIFICATION: %s;%s;%s;%s;%s" % (contact.get_name(), self.get_name(), state, \
                                                                 command.get_name(), self.output))

    # Raise a log entry with a Eventhandler alert like
    # HOST NOTIFICATION: superadmin;server;UP;notify-by-rss;no output
    def raise_event_handler_log_entry(self, command):
        if self.__class__.log_event_handlers:
            logger.log("HOST EVENT HANDLER: %s;%s;%s;%s;%s" % (self.get_name(), self.state, self.state_type, self.attempt, \
                                                                 command.get_name()))


    #Raise a log entry with FLAPPING START alert like
    #HOST FLAPPING ALERT: server;STARTED; Host appears to have started flapping (50.6% change >= 50.0% threshold)
    def raise_flapping_start_log_entry(self, change_ratio, threshold):
        logger.log("HOST FLAPPING ALERT: %s;STARTED; Host appears to have started flapping (%.1f%% change >= %.1f%% threshold)" % \
                      (self.get_name(), change_ratio, threshold))


    #Raise a log entry with FLAPPING STOP alert like
    #HOST FLAPPING ALERT: server;STOPPED; host appears to have stopped flapping (23.0% change < 25.0% threshold)
    def raise_flapping_stop_log_entry(self, change_ratio, threshold):
        logger.log("HOST FLAPPING ALERT: %s;STOPPED; Host appears to have stopped flapping (%.1f%% change < %.1f%% threshold)" % \
                      (self.get_name(), change_ratio, threshold))


    #If there is no valid time for next check, raise a log entry
    def raise_no_next_check_log_entry(self):
        logger.log("Warning : I cannot schedule the check for the host '%s' because there is not future valid time" % \
                      (self.get_name()))

    #Raise a log entry when a downtime begins
    #HOST DOWNTIME ALERT: test_host_0;STARTED; Host has entered a period of scheduled downtime
    def raise_enter_downtime_log_entry(self):
        logger.log("HOST DOWNTIME ALERT: %s;STARTED; Host has entered a period of scheduled downtime" % \
                      (self.get_name()))


    #Raise a log entry when a downtime has finished
    #HOST DOWNTIME ALERT: test_host_0;STOPPED; Host has exited from a period of scheduled downtime
    def raise_exit_downtime_log_entry(self):
        logger.log("HOST DOWNTIME ALERT: %s;STOPPED; Host has exited from a period of scheduled downtime" % \
                      (self.get_name()))


    #Raise a log entry when a downtime prematurely ends
    #HOST DOWNTIME ALERT: test_host_0;CANCELLED; Service has entered a period of scheduled downtime
    def raise_cancel_downtime_log_entry(self):
        logger.log("HOST DOWNTIME ALERT: %s;CANCELLED; Scheduled downtime for host has been cancelled." % \
                      (self.get_name()))


    #Is stalking ?
    #Launch if check is waitconsume==first time
    #and if c.status is in self.stalking_options
    def manage_stalking(self, c):
        need_stalk = False
        if c.status == 'waitconsume':
            if c.exit_status == 0 and 'o' in self.stalking_options:
                need_stalk = True
            elif c.exit_status == 1 and 'd' in self.stalking_options:
                need_stalk = True
            elif c.exit_status == 2 and 'd' in self.stalking_options:
                need_stalk = True
            elif c.exit_status == 3 and 'u' in self.stalking_options:
                need_stalk = True
            if c.output != self.output:
                need_stalk = False
        if need_stalk:
            logger.log("Stalking %s : %s" % (self.get_name(), self.output))


    #fill act_depend_of with my parents (so network dep)
    #and say parents they impact me, no timeperiod and folow parents of course
    def fill_parents_dependancie(self):
        for parent in self.parents:
            if parent is not None:
                #I add my parent in my list
                self.act_depend_of.append( (parent, ['d', 'u', 's', 'f'], 'network_dep', None, True) )

                #And I register myself in my parent list too
                parent.register_child(self)

                # And add the parent/child dep filling too, for broking
                parent.register_son_in_parent_child_dependencies(self)


    # Register a child in our lists
    def register_child(self, child):
        # We've got 2 list : a list for our child
        # where we just put the pointer, it's jsut for broking
        # and anotehr with all data, useful for 'running' part
        self.childs.append(child)
        self.act_depend_of_me.append( (child, ['d', 'u', 's', 'f'], 'network_dep', None, True) )


    #Give data for checks's macros
    def get_data_for_checks(self):
        return [self]

    #Give data for event handler's macro
    def get_data_for_event_handler(self):
        return [self]

    #Give data for notifications'n macros
    def get_data_for_notifications(self, contact, n):
        return [self, contact, n]


    #See if the notification is launchable (time is OK and contact is OK too)
    def notification_is_blocked_by_contact(self, n, contact):
        return not contact.want_host_notification(self.last_chk, self.state, n.type, self.criticity)


    #MACRO PART
    def get_duration_sec(self):
        return str(int(self.duration_sec))


    def get_duration(self):
        m, s = divmod(self.duration_sec, 60)
        h, m = divmod(m, 60)
        return "%02dh %02dm %02ds" % (h, m, s)


    #Check if a notification for this host is suppressed at this time
    #This is a check at the host level. Do not look at contacts here
    def notification_is_blocked_by_item(self, type, t_wished = None):
        if t_wished is None:
            t_wished = time.time()

        # TODO
        # forced notification -> false
        # custom notification -> false

        # Block if notifications are program-wide disabled
        if not self.enable_notifications:
            return True

        # Does the notification period allow sending out this notification?
        if self.notification_period is not None and not self.notification_period.is_time_valid(t_wished):
            return True

        # Block if notifications are disabled for this host
        if not self.notifications_enabled:
            return True

        # Block if the current status is in the notification_options d,u,r,f,s
        if 'n' in self.notification_options:
            return True

        if type in ('PROBLEM', 'RECOVERY'):
            if self.state == 'DOWN' and not 'd' in self.notification_options:
                return True
            if self.state == 'UP' and not 'r' in self.notification_options:
                return True
            if self.state == 'UNREACHABLE' and not 'u' in self.notification_options:
                return True
        if (type in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED')
                and not 'f' in self.notification_options):
            return True
        if (type in ('DOWNTIMESTART', 'DOWNTIMEEND', 'DOWNTIMECANCELLED')
                and not 's' in self.notification_options):
            return True

        # Acknowledgements make no sense when the status is ok/up
        if type == 'ACKNOWLEDGEMENT':
            if self.state == self.ok_up:
                return True

        # Flapping
        if type in ('FLAPPINGSTART', 'FLAPPINGSTOP', 'FLAPPINGDISABLED'):
        # todo    block if not notify_on_flapping
            if self.scheduled_downtime_depth > 0:
                return True

        # When in deep downtime, only allow end-of-downtime notifications
        # In depth 1 the downtime just started and can be notified
        if self.scheduled_downtime_depth > 1 and not type in ('DOWNTIMEEND', 'DOWNTIMECANCELLED'):
            return True

        # Block if in a scheduled downtime and a problem arises
        if self.scheduled_downtime_depth > 0 and type in ('PROBLEM', 'RECOVERY'):
            return True

        # Block if the status is SOFT
        if self.state_type == 'SOFT' and type == 'PROBLEM':
            return True

        # Block if the problem has already been acknowledged
        if self.problem_has_been_acknowledged and type != 'ACKNOWLEDGEMENT':
            return True

        # Block if flapping
        if self.is_flapping:
            return True

        return False


    #Get a oc*p command if item has obsess_over_*
    #command. It must be enabled locally and globally
    def get_obsessive_compulsive_processor_command(self):
        cls = self.__class__
        if not cls.obsess_over or not self.obsess_over_host:
            return

        m = MacroResolver()
        data = self.get_data_for_event_handler()
        cmd = m.resolve_command(cls.ochp_command, data)
        e = EventHandler(cmd, timeout=cls.ochp_timeout)

        #ok we can put it in our temp action queue
        self.actions.append(e)



    # Macro part
    def get_total_services(self):
        return str(len(self.services))


    def get_total_services_ok(self):
        return str(len([s for s in self.services if s.state_id == 0]))


    def get_total_services_warning(self):
        return str(len([s for s in self.services if s.state_id == 1]))


    def get_total_services_critical(self):
        return str(len([s for s in self.services if s.state_id == 2]))


    def get_total_services_unknown(self):
        return str(len([s for s in self.services if s.state_id == 3]))


    def get_ack_author_name(self):
        if self.acknowledgement is None:
            return ''
        return self.acknowledgement.author


    def get_ack_comment(self):
        if self.acknowledgement is None:
            return ''
        return self.acknowledgement.comment


    def get_check_command(self):
        return self.check_command.get_name()





# CLass for the hosts lists. It's mainly for configuration
# part
class Hosts(Items):
    name_property = "host_name" #use for the search by name
    inner_class = Host #use for know what is in items


    #prepare_for_conf_sending to flatten some properties
    def prepare_for_sending(self):
        for h in self:
            h.prepare_for_conf_sending()


    # Create link between elements:
    # hosts -> timeperiods
    # hosts -> hosts (parents, etc)
    # hosts -> commands (check_command)
    # hosts -> contacts
    def linkify(self, timeperiods=None, commands=None, contacts=None, realms=None, resultmodulations=None, criticitymodulations=None, escalations=None, hostgroups=None):
        self.linkify_with_timeperiods(timeperiods, 'notification_period')
        self.linkify_with_timeperiods(timeperiods, 'check_period')
        self.linkify_with_timeperiods(timeperiods, 'maintenance_period')
        self.linkify_h_by_h()
        self.linkify_h_by_hg(hostgroups)
        self.linkify_one_command_with_commands(commands, 'check_command')
        self.linkify_one_command_with_commands(commands, 'event_handler')

        self.linkify_with_contacts(contacts)
        self.linkify_h_by_realms(realms)
        self.linkify_with_resultmodulations(resultmodulations)
        self.linkify_with_criticitymodulations(criticitymodulations)
        # WARNING: all escalations will not be link here
        # (just the escalation here, not serviceesca or hostesca).
        # This last one will be link in escalations linkify.
        self.linkify_with_escalations(escalations)


    # Fill adress by host_name if not set
    def fill_predictive_missing_parameters(self):
        for h in self:
            h.fill_predictive_missing_parameters()


    # Link host with hosts (parents)
    def linkify_h_by_h(self):
        for h in self:
            parents = h.parents
            #The new member list
            new_parents = []
            for parent in parents:
                parent = parent.strip()
                p = self.find_by_name(parent)
                if p is not None:
                    new_parents.append(p)
                else:
                    err = "Error : the parent '%s' on host '%s' is unknown!" % (parent, h.get_name())
                    self.configuration_errors.append(err)
            #print "Me,", h.host_name, "define my parents", new_parents
            #We find the id, we remplace the names
            h.parents = new_parents


    # Link with realms and set a default realm if none
    def linkify_h_by_realms(self, realms):
        default_realm = None
        for r in realms:
            if getattr(r, 'default', False):
                default_realm = r
        #if default_realm is None:
        #    print "Error : there is no default realm defined!"
        for h in self:
            if h.realm is not None:
                p = realms.find_by_name(h.realm.strip())
                if p is None:
                    err = "Error : the host %s got a invalid realm (%s)!" % (h.get_name(), h.realm)
                    h.configuration_errors.append(err)
                h.realm = p
            else:
                #print "Notice : applying default realm %s to host %s" % (default_realm.get_name(), h.get_name())
                h.realm = default_realm
                h.got_default_realm = True


    # We look for hostgroups property in hosts and
    # link them
    def linkify_h_by_hg(self, hostgroups):
        # Register host in the hostgroups
        for h in self:
            if not h.is_tpl():
                new_hostgroups = []
                if hasattr(h, 'hostgroups') and h.hostgroups != '':
                    hgs = h.hostgroups.split(',')
                    for hg_name in hgs:
                        hg_name = hg_name.strip()
                        hg = hostgroups.find_by_name(hg_name)
                        if hg is not None:
                            new_hostgroups.append(hg)
                        else:
                            err = "Error : the hostgroup '%s' of the host '%s' is unknown" % (hg_name, h.host_name)
                            h.configuration_errors.append(err)
                h.hostgroups = new_hostgroups



    # It's used to change old Nagios2 names to
    # Nagios3 ones
    def old_properties_names_to_new(self):
        for h in self:
            h.old_properties_names_to_new()



    # We look for hostgroups property in hosts and
    def explode(self, hostgroups, contactgroups):
        # Register host in the hostgroups
        for h in self:
            if not h.is_tpl() and hasattr(h, 'host_name'):
                hname = h.host_name
                if hasattr(h, 'hostgroups'):
                    hgs = h.hostgroups.split(',')
                    for hg in hgs:
                        hostgroups.add_member(hname, hg.strip())

        # items::explode_contact_groups_into_contacts
        # take all contacts from our contact_groups into our contact property
        self.explode_contact_groups_into_contacts(contactgroups)



    # Create depenancies:
    # Depencies at the host level: host parent
    def apply_dependancies(self):
        for h in self:
            h.fill_parents_dependancie()


    # Parent graph: use to find quickly relations between all host, and loop
    # return True if tehre is a loop
    def no_loop_in_parents(self):
        # Ok, we say "from now, no loop :) "
        r = True

        # Create parent graph
        parents = Graph()

        # With all hosts as nodes
        for h in self:
            if h is not None:
                parents.add_node(h)

        # And now fill edges
        for h in self:
            for p in h.parents:
                if p is not None:
                    parents.add_edge(p, h)

        # Now get the list of all hosts in a loop
        host_in_loops = parents.loop_check()

        # and raise errors about it
        for h in host_in_loops:
            logger.log("Error: The host '%s' is part of a circular parent/child chain!" % h.get_name())
            r = False

        return r


    # Return a list of the host_name of the hosts
    # that gotthe template with name=tpl_name
    def find_hosts_that_use_template(self, tpl_name):
        res = []
        # first find the template
        tpl = None
        for h in self:
            # Look for template with the good name
            if h.is_tpl() and hasattr(h, 'name') and h.name.strip() == tpl_name.strip():
                tpl = h

        # If we find noone, we return nothing (easy case:) )
        if tpl is None:
            return []

        # Ok, we find the tpl
        for h in self:
            if tpl in h.templates and hasattr(h, 'host_name'):
                res.append(h.host_name)

        return res


    # Will create all business tree for the
    # services
    def create_business_rules(self, hosts, services):
        for h in self:
            h.create_business_rules(hosts, services)


    # Will link all business service/host with theirs
    # dep for problem/impact link
    def create_business_rules_dependencies(self):
        for h in self:
            h.create_business_rules_dependencies()
