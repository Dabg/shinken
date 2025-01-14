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


"""
This file is to be imported by every Shinken service component:
Arbiter, Scheduler, etc. It just checks for the main requirement of
Shinken.
"""

import sys

VERSION = "0.6.5"

# Make sure people are using Python 2.4 or higher
if sys.version_info < (2,4):
    sys.exit("Shinken requires as a minimum Python 2.4.x, sorry")
elif sys.version_info >= (3,):
    sys.exit("Shinken is not yet compatible with Python 3.x, sorry")

try:
    import shinken.pyro_wrapper
except ImportError:
    sys.exit("Shinken requires the Python Pyro module. Please install it.")
