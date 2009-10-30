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


#Scheduler is like a satellite for dispatcher
from satellitelink import SatelliteLink, SatelliteLinks
from util import to_int, to_bool
from item import Items

class SchedulerLink(SatelliteLink):
    id = 0
    properties={'name' : {'required' : True },#, 'pythonize': None},
                'address' : {'required' : True},#, 'pythonize': to_bool},
                'port' : {'required':  True, 'pythonize': to_int},
                'spare' : {'required':  False, 'default' : '0', 'pythonize': to_bool},
                }
 
    running_properties = {'is_active' : {'default' : False},
                          'con' : {'default' : None}
                          #self.is_alive = False
                          }
    macros = {}


    def get_name(self):
        return self.name


    def run_external_command(self, command):
        if self.con == None:
            self.create_connexion()
        if not self.is_alive():
            return None
        self.con.run_external_command(command)


    def register_to_my_pool(self):
        self.pool.schedulers.append(self)


class SchedulerLinks(SatelliteLinks):#(Items):
    name_property = "name"
    inner_class = SchedulerLink

