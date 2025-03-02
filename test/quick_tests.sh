#!/bin/bash
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


DIR=$(cd $(dirname "$0"); pwd)
cd $DIR
echo `pwd`

#delete the resul of nosetest, for coverage
rm -f nosetests.xml
rm -f coverage.xml
rm -f .coverage

function launch_and_assert {
    SCRIPT=$1
#    nosetests -v -s --with-xunit --with-coverage ./$SCRIPT
    ./$SCRIPT
    if [ $? != 0 ]
	then
	echo "Error : the test $SCRIPT failed"
	exit 2
    fi
}

#Launching only quick tests for quick regression check
#for ii in `ls -1 test_*py`; do echo "Launching Test $ii" && python $ii; done
launch_and_assert test_system_time_change.py
launch_and_assert test_services.py
launch_and_assert test_hosts.py
launch_and_assert test_host_missing_adress.py
launch_and_assert test_not_hostname.py
launch_and_assert test_bad_contact_call.py
launch_and_assert test_action.py
launch_and_assert test_config.py
launch_and_assert test_dependencies.py
launch_and_assert test_npcdmod.py
launch_and_assert test_problem_impact.py
launch_and_assert test_timeperiods.py
launch_and_assert test_command.py
launch_and_assert test_module_simplelog.py
launch_and_assert test_module_service_perfdata.py
launch_and_assert test_module_host_perfdata.py
launch_and_assert test_module_pickle_retention.py
launch_and_assert test_service_tpl_on_host_tpl.py
launch_and_assert test_db.py
launch_and_assert test_macroresolver.py
launch_and_assert test_complex_hostgroups.py
launch_and_assert test_resultmodulation.py
launch_and_assert test_satellites.py
launch_and_assert test_illegal_names.py
launch_and_assert test_service_generators.py
launch_and_assert test_notifway.py
launch_and_assert test_eventids.py
launch_and_assert test_obsess.py
launch_and_assert test_commands_perfdata.py
launch_and_assert test_notification_warning.py
launch_and_assert test_timeperiod_inheritance.py
launch_and_assert test_bad_timeperiods.py
launch_and_assert test_external_commands.py
launch_and_assert test_on_demand_event_handlers.py
launch_and_assert test_business_correlator.py
launch_and_assert test_properties.py
launch_and_assert test_realms.py
launch_and_assert test_host_without_cmd.py
launch_and_assert test_escalations.py
launch_and_assert test_notifications.py
launch_and_assert test_contactdowntimes.py
launch_and_assert test_nullinheritance.py
launch_and_assert test_create_link_from_ext_cmd.py
launch_and_assert test_dispatcher.py
launch_and_assert test_module_hot_dependencies_arbiter.py
launch_and_assert test_module_hack_cmd_poller_tag.py
launch_and_assert test_unknown_do_not_change.py
launch_and_assert test_customs_on_service_hosgroups.py
launch_and_assert test_modules_nrpe_poller.py
launch_and_assert test_poller_tag_get_checks.py
launch_and_assert test_reactionner_tag_get_notif.py
launch_and_assert test_orphaned.py
launch_and_assert test_module_pickle_retention_broker.py
launch_and_assert test_module_pickle_retention_arbiter.py
launch_and_assert test_module_nagios_retention.py
launch_and_assert test_discovery_def.py
launch_and_assert test_hostgroup_no_host.py
launch_and_assert test_nocontacts.py
launch_and_assert test_srv_nohost.py
launch_and_assert test_srv_badhost.py
launch_and_assert test_module_named_pipe_arbiter.py
launch_and_assert test_nohostsched.py
launch_and_assert test_modulemanager.py
launch_and_assert test_clean_sched_queues.py
launch_and_assert test_bad_notification_period.py
launch_and_assert test_no_notification_period.py
launch_and_assert test_strange_characters_commands.py
launch_and_assert test_startmember_group.py
launch_and_assert test_nested_hostgroups.py
launch_and_assert test_contactgroup_nomembers.py
launch_and_assert test_service_nohost.py
launch_and_assert test_bad_sat_realm_conf.py
launch_and_assert test_bad_realm_conf.py
launch_and_assert test_no_broker_in_realm_warning.py
launch_and_assert test_critmodulation.py
launch_and_assert test_hostdep_withno_depname.py
launch_and_assert test_service_withhost_exclude.py

launch_and_assert test_maintenance_period.py
#Live status is a bit longer than the previous, so we put it at the end.
launch_and_assert test_livestatus.py

# Can failed on non prepared box
launch_and_assert test_bad_start.py

# And create the coverage file
coverage xml --omit=/usr/lib

echo "All quick unit tests passed :)"
echo "But please launch a test.sh pass too for long tests too!"
