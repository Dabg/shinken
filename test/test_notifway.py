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
    #setUp is in shinken_test
    def setUp(self):
        self.setup_with_file('etc/nagios_notif_way.cfg')


    #Change ME :)
    def test_contact_def(self):
        #
        # Config is not correct because of a wrong relative path 
        # in the main config file
        #
        print "Get the contact"
        now = time.time()
        contact = self.sched.contacts.find_by_name("test_contact")
        print "The service", contact.__dict__

        print "All notification Way :"
        for nw in self.sched.notificationways:
            print "\t", nw

        email_in_day = self.sched.notificationways.find_by_name('email_in_day')
        self.assert_(email_in_day in contact.notificationways)

        sms_the_night = self.sched.notificationways.find_by_name('sms_the_night')
        self.assert_(sms_the_night in contact.notificationways)

        print "Contact notification way(s) :"
        for nw in contact.notificationways:
            print "\t", nw


if __name__ == '__main__':
    unittest.main()

