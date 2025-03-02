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

#The resultmodulation class is used for in scheduler modulation of resulsts
#like the return code or the output.

import time

from item import Item, Items

from shinken.property import StringProp, IntegerProp

class Criticitymodulation(Item):
    id = 1#0 is always special in database, so we do not take risk here
    my_type = 'criticitymodulation'

    properties = Item.properties.copy()
    properties.update({
        'criticitymodulation_name': StringProp(),
        'criticity':                IntegerProp(),
        'modulation_period':        StringProp(default=None),
    })
    

    # For debugging purpose only (nice name)
    def get_name(self):
        return self.resultmodulation_name



class Criticitymodulations(Items):
    name_property = "criticitymodulation_name"
    inner_class = Criticitymodulation


    def linkify(self, timeperiods):
        self.linkify_cm_by_tp(timeperiods)


    # We just search for each timeperiod the tp
    # and replace the name by the tp
    def linkify_cm_by_tp(self, timeperiods):
        for rm in self:
            mtp_name = rm.modulation_period.strip()

            # The new member list, in id
            mtp = timeperiods.find_by_name(mtp_name)

            if mtp_name != '' and mtp is None:
                err = "Error : the criticty modulation '%s' got an unknown modulation_period '%s'" % (rm.get_name(), mtp_name)
                rm.configuration_errors.append(err)

            rm.modulation_period = mtp
