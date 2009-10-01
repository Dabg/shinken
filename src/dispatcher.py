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


#This is the class of the dispatcher. It's role is to dispatch 
#configurations to other elements like schedulers, reactionner, 
#pollers and brokers. It is responsible for hight avaibility part. If an
#element die and the element type have a spare, it send the confi of the 
#dead to the spare,


import Pyro.core

from util import scheduler_no_spare_first, alive_then_spare_then_deads


#Dispatcher Class
class Dispatcher:
    #Load all elements, set them no assigned
    # and add them to elements, so loop will be easier :)
    def __init__(self, conf):
        #Pointer to the whole conf
        self.conf = conf
        #Direct pointer to importants elements for us
        self.schedulerlinks = self.conf.schedulerlinks
        self.reactionners = self.conf.reactionners
        self.brokers = self.conf.brokers
        self.pollers = self.conf.pollers
        self.dispatch_queue = {'schedulers' : [], 'reactionners' : [],
                               'brokers' : [], 'pollers' : []}
        self.elements = []
        for cfg in self.conf.confs.values():
            cfg.is_assigned = False
            cfg.assigned_to = None
            #self.elements.append(cfg)
        for sched in self.schedulerlinks:
            sched.is_active = False
            sched.alive = False
            sched.conf = None
            self.elements.append(sched)
        for reactionner in self.reactionners:
            reactionner.is_active = False
            reactionner.alive = False
            self.elements.append(reactionner)
        for poller in self.pollers:
            poller.is_active = False
            poller.alive = False
            self.elements.append(poller)
        self.dispatch_ok = False
        self.first_dispatch_done = False

    
    #checks alive elements
    def check_alive(self):
        for elt in self.elements:
            elt.alive = elt.is_alive()
            print "Element is alive?", elt.alive, "is active?", elt.is_active
            


    #Check if all active items are still alive
    #the result go into self.dispatch_ok
    def check_dispatch(self):
        print "Check dispatch", self.dispatch_ok
        for elt in self.elements:
            print "Elt:", elt.__dict__, elt.is_active, elt.alive
            if elt.is_active and not elt.alive:
                self.dispatch_ok = False
                print "Set dispatch False"
                if hasattr(elt, 'conf'):
                    if elt.conf != None:
                        elt.conf.assigned_to = None
                        elt.conf.is_assigned = False
                    elt.is_active = False
                else:
                    print 'No conf'

    
    #Manage the dispatch
    def dispatch(self):
        #Is no need to dispatch, do not dispatch :)
        if not self.dispatch_ok:
            conf_to_dispatch = [cfg for cfg in self.conf.confs.values() if cfg.is_assigned==False]
            nb_conf = len(conf_to_dispatch)

            print "Dispatching ", nb_conf, "configurations"            
            #get scheds, alive and no spare first
            print 'T', self.schedulerlinks.items.values().sort()
            scheds = self.schedulerlinks.items.values()
            scheds.sort(alive_then_spare_then_deads)
            scheds.reverse() #pop is last, I need first
            
            for conf in conf_to_dispatch:
                sched = scheds.pop()
                if not sched.is_active:
                    print "Dispatching conf", sched.id
                    try:
                        sched.put_conf(conf)
                        sched.conf = conf
                        sched.is_active = True
                        conf.is_assigned = True
                        conf.assigned_to = sched
                    except Pyro.errors.URIError as exp:
                        print exp
                    except Pyro.errors.ProtocolError as exp:
                        print exp

            #We pop conf to dispatch, so it must be no more conf...
            nb_missed = len(conf_to_dispatch)
            if nb_missed > 0:
                print "WARNING : All configurations are not dispatched ", nb_missed, "are missing"
            else:
                print "OK, all configurations are dispatched :)"
                self.dispatch_ok = True
                
            #TODO : more python
            tmp_conf = {}
            tmp_conf['schedulers'] = {}
            i = 0
            for sched in self.conf.schedulerlinks:
                tmp_conf['schedulers'][i] = {'port' : sched.port, 'address' : sched.address, 'name' : sched.name, 'instance_id' : sched.id}
                i += 1
            
            for reactionner in self.conf.reactionners.items.values():
                reactionner.put_conf(tmp_conf)

            for broker in self.conf.brokers.items.values():
                broker.put_conf(tmp_conf)


            #TODO : clean and link
            #Now Poller
            tmp_conf = {}
            tmp_conf['schedulers'] = {}
            i = 0
            sched = self.conf.schedulerlinks[0]
            tmp_conf['schedulers'][i] = {'port' : sched.port, 'address' : sched.address}
            
            
            for poller in self.conf.pollers.items.values():
                poller.put_conf(tmp_conf)


