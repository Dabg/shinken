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


from command import CommandCall
from item import Item, Items
from util import to_int, to_char, to_split, to_bool

class Contact(Item):
    id = 0
    properties={'contact_name' : {'required':True},
                'alias' : {'required':False, 'default':'none'},
                'contactgroups' : {'required':False, 'default':''},
                'host_notifications_enabled' : {'required':True, 'pythonize': to_bool},
                'service_notifications_enabled' : {'required':True, 'pythonize': to_bool},
                'host_notification_period' : {'required':True},
                'service_notification_period' : {'required':True},
                'host_notification_options' : {'required':True, 'pythonize': to_split},
                'service_notification_options' : {'required':True, 'pythonize': to_split},
                'host_notification_commands' : {'required':True},
                'service_notification_commands' : {'required':True},
                'email' : {'required' : False, 'default':'none'},
                'pager' : {'required' : False, 'default':'none'},
                'addressx' : {'required' : False, 'default':'none'},
                'can_submit_commands' : {'required' : False, 'default':'0', 'pythonize': to_bool},
                'retain_status_information' : {'required' : False, 'default':'1', 'pythonize': to_bool},
                'retain_nonstatus_information' : {'required' : False, 'default':'1', 'pythonize': to_bool}
                }

    running_properties = {}

    
    macros = {
        'CONTACTNAME' : 'contact_name',
        'CONTACTALIAS' : 'alias',
        'CONTACTEMAIL' : 'email',
        'CONTACTPAGER' : 'pager',
        'CONTACTADDRESSn' : 'addressx',
        'CONTACTGROUPNAME' : 'get_groupname',
        'CONTACTGROUPNAMES' : 'get_groupnames'
        }

    #Search for notification_options with state and if t is in service_notification_period
    def want_service_notification(self, t, state):
        #print self
        b = self.service_notification_period.is_time_valid(t)
        if 'n' in self.service_notification_options:
            return False
        t = {'WARNING' : 'w', 'UNKNOWN' : 'u', 'CRITICAL' : 'c',
             'RECOVERY' : 'r', 'FLAPPING' : 'f', 'DOWNTIME' : 's'}
        if state in t:
            #print 'State:', t[state] in self.service_notification_options, 'b:', b,self
            return b and t[state] in self.service_notification_options
        return False

    #Search for notification_options with state and if t is in host_notification_period
    def want_host_notification(self, t, state):
        #print self
        b = self.host_notification_period.is_time_valid(t)
        if 'n' in self.host_notification_options:
            return False
        t = {'DOWN' : 'd', 'UNREABLE' : 'u', 'RECOVERY' : 'r',
             'FLAPPING' : 'f', 'DOWNTIME' : 's'}
        if state in t:
            return b and t[state] in self.host_notification_options
        return False


    def clean(self):
        pass


class Contacts(Items):
    name_property = "contact_name"
    inner_class = Contact

    def linkify(self, timeperiods, commands):
        self.linkify_c_by_tp(timeperiods)
        self.linkify_c_by_cmd(commands)

    
    #We just search for each timeperiod the id of the tp
    #and replace the name by the id
    def linkify_c_by_tp(self, timeperiods):
        for c in self:#.items:
            #c = self.items[id]
            #service notif period
            sntp_name = c.service_notification_period
            #host notf period
            hntp_name = c.host_notification_period

            #The new member list, in id
            sntp = timeperiods.find_by_name(sntp_name)
            hntp = timeperiods.find_by_name(hntp_name)
            
            c.service_notification_period = sntp
            c.host_notification_period = hntp


    #Simplify hosts commands by commands id
    def linkify_c_by_cmd(self, commands):
        for c in self:#.items:
            tmp = []
            for cmd in c.service_notification_commands.split(','):
                tmp.append(CommandCall(commands,cmd))
            c.service_notification_commands = tmp

            tmp = []
            for cmd in c.host_notification_commands.split(','):
                tmp.append(CommandCall(commands,cmd))
            c.host_notification_commands = tmp


    #We look for contacts property in contacts and
    def explode(self, contactgroups):
        #Hostgroups property need to be fullfill for got the informations
        self.apply_partial_inheritance('contactgroups')
        for c in self:#.items:
            #c = self.items[id]
            if not c.is_tpl():
                cname = c.contact_name
                if c.has('contactgroups'):
                    cgs = c.contactgroups.split(',')
                    for cg in cgs:
                        contactgroups.add_member(cname, cg.strip())

