#!/usr/bin/env python
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


from util import to_split, to_bool
from item import Item, Items

class Servicedependency(Item):
    id = 0
    
#F is dep of D
#host_name			Host B
#	service_description		Service D
#	dependent_host_name		Host C
#	dependent_service_description	Service F
#	execution_failure_criteria	o
#	notification_failure_criteria	w,u
#       inherits_parent		1
#       dependency_period       24x7

    properties={'dependent_host_name' : {'required':True},
                'dependent_hostgroup_name' : {'required':False, 'default' : ''},
                'dependent_service_description' : {'required':True},
                'host_name' : {'required':True},
                'hostgroup_name' : {'required':False, 'default' : ''},
                'service_description' : {'required':True},
                'inherits_parent' : {'required':False, 'default' : '0', 'pythonize' : to_bool},
                'execution_failure_criteria' : {'required':False, 'default' : 'n', 'pythonize' : to_split},
                'notification_failure_criteria' : {'required':False, 'default' : 'n', 'pythonize' : to_split},
                'dependency_period' : {'required':False, 'default' : ''}
                }
    
    running_properties = {}


    #Give a nice name output, for debbuging purpose
    #(Yes, debbuging CAN happen...)
    def get_name(self):
        return self.dependent_host_name+'/'+self.dependent_service_description+'..'+self.host_name+'/'+self.service_description



class Servicedependencies(Items):
    def delete_servicesdep_by_id(self, ids):
        for id in ids:
            del self.items[id]


    #We create new servicedep if necessery (host groups and co)
    def explode(self):
        #The "old" services will be removed. All services with 
        #more than one host or a host group will be in it
        srvdep_to_remove = []
        
        #Then for every host create a copy of the service with just the host
        #because we are adding services, we can't just loop in it
        servicedeps = self.items.keys() 
        for id in servicedeps:
            sd = self.items[id]
            if not sd.is_tpl(): #Exploding template is useless
                print sd
                if not hasattr(sd, 'dependent_host_name'):
                    sd.dependent_host_name = sd.host_name
                hnames = sd.dependent_host_name.split(',')
                snames = sd.dependent_service_description.split(',')
                couples = []
                for hname in hnames:
                    for sname in snames:
                        couples.append((hname, sname))
                if len(couples) >= 2:
                    for (hname, sname) in couples:
                        hname = hname.strip()
                        sname = sname.strip()
                        new_sd = sd.copy()
                        new_sd.dependent_host_name = hname
                        new_sd.dependent_service_description = sname
                        self.items[new_sd.id] = new_sd
                    srvdep_to_remove.append(id)        
        self.delete_servicesdep_by_id(srvdep_to_remove)


    def linkify(self, hosts, services, timeperiods):
        self.linkify_sd_by_s(hosts, services)
        self.linkify_sd_by_tp(timeperiods)
        self.linkify_s_by_sd()


    #We just search for each srvdep the id of the srv
    #and replace the name by the id
    def linkify_sd_by_s(self, hosts, services):
        for sd in self:
            try:
                s_name = sd.dependent_service_description
                hst_name = sd.dependent_host_name

                #The new member list, in id
                s = services.find_srv_by_name_and_hostname(hst_name, s_name)
                sd.dependent_service_description = s
                
                s_name = sd.service_description
                hst_name = sd.host_name
                
                #The new member list, in id
                s = services.find_srv_by_name_and_hostname(hst_name, s_name)
                sd.service_description = s
                
            except AttributeError as exp:
                print exp


    #We just search for each srvdep the id of the srv
    #and replace the name by the id
    def linkify_sd_by_tp(self, timeperiods):
        for sd in self:
            try:
                tp_name = sd.dependency_period
                tp = timeperiods.find_by_name(tp_name)
                sd.dependency_period = tp
            except AttributeError as exp:
                print exp


    #We backport service dep to service. So SD is not need anymore
    def linkify_s_by_sd(self):
        for sd in self:
            if not sd.is_tpl():
                s = sd.dependent_service_description
                if s is not None:
                    if hasattr(sd, 'dependency_period'):
                        s.add_service_act_dependancy(sd.service_description, sd.notification_failure_criteria, sd.dependency_period)
                        s.add_service_chk_dependancy(sd.service_description, sd.execution_failure_criteria, sd.dependency_period)
                    else:
                        s.add_service_act_dependancy(sd.service_description, sd.notification_failure_criteria, None)
                        s.add_service_chk_dependancy(sd.service_description, sd.execution_failure_criteria, None)


    #Apply inheritance for all properties
    def apply_inheritance(self, hosts):
        #We check for all Host properties if the host has it
        #if not, it check all host templates for a value
        for prop in Servicedependency.properties:
            self.apply_partial_inheritance(prop)

        #Then implicit inheritance
        #self.apply_implicit_inheritance(hosts)
        for s in self:
            s.get_customs_properties_by_inheritance(self)
