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


import sys

from ndodb_mysql_broker import Ndodb_Mysql_broker, properties


#called by the plugin manager to get a instance
def get_instance(mod_conf):

    print "Get a ndoDB instance for plugin %s" % mod_conf.get_name()

    #First try to import
    #try:
    #
    #except ImportError , exp:
    #    print "Warning : the plugin type %s is unavalable : %s" % ('ndo_mysql', exp)
    #    return None

    if not hasattr( mod_conf, 'character_set'):
        mod_conf.character_set = 'utf8'
    if not hasattr(mod_conf, 'nagios_mix_offset'):
        mod_conf.nagios_mix_offset = '0'
    instance = Ndodb_Mysql_broker(mod_conf)
    return instance
