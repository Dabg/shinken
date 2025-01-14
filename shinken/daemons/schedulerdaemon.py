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

import os
import time
import traceback

from shinken.scheduler import Scheduler
from shinken.macroresolver import MacroResolver
from shinken.external_command import ExternalCommandManager
from shinken.daemon import Daemon
from shinken.property import PathProp, IntegerProp
import shinken.pyro_wrapper as pyro
from shinken.log import logger
from shinken.satellite import BaseSatellite, IForArbiter as IArb, Interface

#Interface for Workers

class IChecks(Interface):
    """ Interface for Workers:
They connect here and see if they are still OK with our running_id, if not, they must drop their checks """

    # poller or reactionner is asking us our running_id
    def get_running_id(self):
        return self.running_id


    # poller or reactionner ask us actions
    def get_checks(self , do_checks=False, do_actions=False, poller_tags=['None'], \
                       reactionner_tags=['None'], worker_name='none', \
                       module_types=['fork']):
        #print "We ask us checks"
        res = self.app.get_to_run_checks(do_checks, do_actions, poller_tags, reactionner_tags, worker_name, module_types)
        #print "Sending %d checks" % len(res)
        self.app.nb_checks_send += len(res)
        return res

    # poller or reactionner are putting us results
    def put_results(self, results):
        nb_received = len(results)
        self.app.nb_check_received += nb_received
        if nb_received != 0:
            print "Received %d results" % nb_received
        self.app.waiting_results.extend(results)

        #for c in results:
        #self.sched.put_results(c)
        return True


class IBroks(Interface):
    """ Interface for Brokers:
They connect here and get all broks (data for brokers). datas must be ORDERED! (initial status BEFORE uodate...) """ 

    # poller or reactionner ask us actions
    def get_broks(self):
        #print "We ask us broks"
        res = self.app.get_broks()
        #print "Sending %d broks" % len(res)#, res
        self.app.nb_broks_send += len(res)
        #we do not more have a full broks in queue
        self.app.has_full_broks = False
        return res

    #A broker is a new one, if we do not have
    #a full broks, we clean our broks, and
    #fill it with all new values
    def fill_initial_broks(self):
        if not self.app.has_full_broks:
            self.app.broks.clear()
            self.app.fill_initial_broks()


class IForArbiter(IArb):
    """ Interface for Arbiter, our big MASTER. We ask him a conf and after we listen for him.
HE got user entry, so we must listen him carefully and give information he want, maybe for another scheduler """

    #arbiter is send us a external coomand.
    #it can send us global command, or specific ones
    def run_external_command(self, command):
        self.app.sched.run_external_command(command)

    def put_conf(self, conf):
        self.app.sched.die()
        super(IForArbiter, self).put_conf(conf)

    #Call by arbiter if it thinks we are running but we must do not (like
    #if I was a spare that take a conf but the master returns, I must die
    #and wait a new conf)
    #Us : No please...
    #Arbiter : I don't care, hasta la vista baby!
    #Us : ... <- Nothing! We are die! you don't follow
    #anything or what??
    def wait_new_conf(self):
        print "Arbiter want me to wait a new conf"
        self.app.sched.die()
        super(IForArbiter, self).wait_new_conf()        


# The main app class
class Shinken(BaseSatellite):

    properties = BaseSatellite.properties.copy()
    properties.update({
        'pidfile':   PathProp(default='schedulerd.pid'),
        'port':      IntegerProp(default='7768'),
        'local_log': PathProp(default='schedulerd.log'),
    })
    
    
    #Create the shinken class:
    #Create a Pyro server (port = arvg 1)
    #then create the interface for arbiter
    #Then, it wait for a first configuration
    def __init__(self, config_file, is_daemon, do_replace, debug, debug_file):
        
        BaseSatellite.__init__(self, 'scheduler', config_file, is_daemon, do_replace, debug, debug_file)

        self.interface = IForArbiter(self)
        self.sched = Scheduler(self)
        
        self.ichecks = None
        self.ibroks = None
        self.must_run = True

        # Now the interface
        self.uri = None
        self.uri2 = None

        # And possible links for satellites
        # from now only pollers
        self.pollers = {}
        self.reactionners = {}


    def do_stop(self):
        if self.pyro_daemon:
            self.pyro_daemon.unregister(self.ibroks)
            self.pyro_daemon.unregister(self.ichecks)
        super(Shinken, self).do_stop()


    def compensate_system_time_change(self, difference):
        """ Compensate a system time change of difference for all hosts/services/checks/notifs """
        logger.log('Warning: A system time change of %d has been detected.  Compensating...' % difference)
        # We only need to change some value
        self.program_start = max(0, self.program_start + difference)

        # Then we compasate all host/services
        for h in self.sched.hosts:
            h.compensate_system_time_change(difference)
        for s in self.sched.services:
            s.compensate_system_time_change(difference)

        # Now all checks and actions
        for c in self.sched.checks.values():
            # Already launch checks should not be touch
            if c.status == 'scheduled':
                t_to_go = c.t_to_go
                ref = c.ref
                new_t = max(0, t_to_go + difference)
                # But it's no so simple, we must match the timeperiod
                new_t = ref.check_period.get_next_valid_time_from_t(new_t)
                # But maybe no there is no more new value! Not good :(
                # Say as error, with error output
                if new_t is None:
                    c.state = 'waitconsume'
                    c.exit_status = 2
                    c.output = '(Error: there is no available check time after time change!)'
                    c.check_time = time.time()
                    c.execution_time = 0
                else:
                    c.t_to_go = new_t
                    ref.next_chk = new_t

        # Now all checks and actions
        for c in self.sched.actions.values():
            # Already launch checks should not be touch
            if c.status == 'scheduled':
                t_to_go = c.t_to_go

                #  Event handler do not have ref
                ref = getattr(c, 'ref', None)
                new_t = max(0, t_to_go + difference)

                # Notification should be check with notification_period
                if c.is_a == 'notification':
                    # But it's no so simple, we must match the timeperiod
                    new_t = ref.notification_period.get_next_valid_time_from_t(new_t)
                    # And got a creation_time variable too
                    c.creation_time = c.creation_time + difference

                # But maybe no there is no more new value! Not good :(
                # Say as error, with error output
                if new_t is None:
                    c.state = 'waitconsume'
                    c.exit_status = 2
                    c.output = '(Error: there is no available check time after time change!)'
                    c.check_time = time.time()
                    c.execution_time = 0
                else:
                    c.t_to_go = new_t


    def manage_signal(self, sig, frame):
        # If we got USR1, just dump memory
        if sig == 10:
            self.sched.need_dump_memory = True
        else: # if not, die :)
            self.sched.die()
            self.must_run = False
            Daemon.manage_signal(self, sig, frame)


    def do_loop_turn(self):        
        # Ok, now the conf
        self.wait_for_initial_conf()
        if not self.new_conf:
            return
        print "Ok we've got conf"
        self.setup_new_conf()
        print "Configuration Loaded"
        self.sched.run()


    def setup_new_conf(self):
        #self.use_ssl = self.app.use_ssl
        (conf, override_conf, modules, satellites) = self.new_conf
        self.new_conf = None
        
        # In fact it make the scheduler just DIE as a bad guy. 
        # Must manage it better or not manage it at all!
        #if self.cur_conf and self.cur_conf.magic_hash == conf.magic_hash:
        #    print("I received a conf with same hash than me, I skip it.")
        #    return
        
        self.conf = conf
        self.cur_conf = conf
        self.override_conf = override_conf
        self.modules = modules
        self.satellites = satellites
        #self.pollers = self.app.pollers

        if self.conf.human_timestamp_log:
            logger.set_human_format()

        # Now We create our pollers
        for pol_id in satellites['pollers']:
            # Must look if we already have it
            already_got = pol_id in self.pollers
            p = satellites['pollers'][pol_id]
            self.pollers[pol_id] = p
            uri = pyro.create_uri(p['address'], p['port'], 'Schedulers', self.use_ssl)
            self.pollers[pol_id]['uri'] = uri
            self.pollers[pol_id]['last_connection'] = 0

        #First mix conf and override_conf to have our definitive conf
        for prop in self.override_conf:
            #print "Overriding the property %s with value %s" % (prop, self.override_conf[prop])
            val = self.override_conf[prop]
            setattr(self.conf, prop, val)

        if self.conf.use_timezone != '':
            print "Setting our timezone to", self.conf.use_timezone
            os.environ['TZ'] = self.conf.use_timezone
            time.tzset()

        if len(self.modules) != 0:
            print "I've got modules", self.modules

        # TODO: if scheduler had previous modules instanciated it must clean them !
        self.modules_manager.set_modules(self.modules)
        self.do_load_modules()
        # And start external ones too
        self.modules_manager.start_external_instances()
        
        # give it an interface
        # But first remove previous interface if exists
        if self.ichecks is not None:
            print "Deconnecting previous Check Interface from pyro_daemon"
            self.pyro_daemon.unregister(self.ichecks)
        #Now create and connect it
        self.ichecks = IChecks(self.sched)
        self.uri = self.pyro_daemon.register(self.ichecks, "Checks")
        print "The Checks Interface uri is:", self.uri

        #Same for Broks
        if self.ibroks is not None:
            print "Deconnecting previous Broks Interface from pyro_daemon"
            self.pyro_daemon.unregister(self.ibroks)
        #Create and connect it
        self.ibroks = IBroks(self.sched)
        self.uri2 = self.pyro_daemon.register(self.ibroks, "Broks")
        print "The Broks Interface uri is:", self.uri2

        print("Loading configuration..")
        self.conf.explode_global_conf()
        
        #we give sched it's conf
        self.sched.reset()
        self.sched.load_conf(self.conf)
        self.sched.load_satellites(self.pollers, self.reactionners)

        #We must update our Config dict macro with good value
        #from the config parameters
        self.sched.conf.fill_resource_macros_names_macros()
        #print "DBG: got macors", self.sched.conf.macros

        #Creating the Macroresolver Class & unique instance
        m = MacroResolver()
        m.init(self.conf)

        #self.conf.dump()
        #self.conf.quick_debug()

        #Now create the external commander
        #it's a applyer : it role is not to dispatch commands,
        #but to apply them
        e = ExternalCommandManager(self.conf, 'applyer')

        #Scheduler need to know about external command to
        #activate it if necessery
        self.sched.load_external_command(e)

        #External command need the sched because he can raise checks
        e.load_scheduler(self.sched)


    # our main function, launch after the init
    def main(self):
        try:
            self.load_config_file()
            self.do_daemon_init_and_start()
            self.uri2 = self.pyro_daemon.register(self.interface, "ForArbiter")
            logger.log("[scheduler] General interface is at: %s" % self.uri2)
            self.do_mainloop()
        except Exception, exp:
            logger.log("CRITICAL ERROR : I got an non recovarable error. I must exit")
            logger.log("You can log a bug ticket at https://sourceforge.net/apps/trac/shinken/newticket for geting help")
            logger.log("Back trace of it: %s" % (traceback.format_exc()))
            raise
            
            
