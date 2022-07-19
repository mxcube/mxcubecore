#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the`
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name]
XalocMachineInfo

[Description]
Hardware Object is used to get relevant machine information
(machine current, time to next injection, status, etc)

[Emitted signals]
- valuesChanged
"""

from __future__ import print_function

import logging
from mxcubecore.BaseHardwareObjects import Equipment

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"


class XalocMachineInfo(Equipment):

    def __init__(self, name):
        Equipment.__init__(self, name)
        self.logger = logging.getLogger('HWR.MachineInfo')
        self.values_dict = dict()
        self.values_dict['mach_current'] = None
        self.values_dict['mach_status'] = ""
        self.values_dict['topup_remaining'] = ""

        self.chan_mach_current = None
        self.chan_mach_status = None
        self.chan_topup_remaining = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        try:
            self.chan_mach_current = self.get_channel_object('MachCurrent')
            if self.chan_mach_current is not None:
                self.chan_mach_current.connect_signal(
                    'update', self.mach_current_changed)

            self.chan_mach_status = self.get_channel_object('MachStatus')
            if self.chan_mach_status is not None:
                self.chan_mach_status.connect_signal('update', self.mach_status_changed)

            self.chan_topup_remaining = self.get_channel_object('TopUpRemaining')
            if self.chan_topup_remaining is not None:
                self.chan_topup_remaining.connect_signal(
                    'update', self.topup_remaining_changed)
        except KeyError:
            self.logger.warning('%s: cannot read machine info', self.name())

    def mach_current_changed(self, value):
        if self.values_dict['mach_current'] is None or\
                abs(self.values_dict['mach_current'] - value) > 0.10:
            self.values_dict['mach_current'] = value
            self.update_values()
            # self.logger.debug('New machine current value=%smA' % value)

    def mach_status_changed(self, status):
        self.values_dict['mach_status'] = str(status).split('.')[-1]
        self.update_values()
        # self.logger.debug('New machine status=%s' % status)

    def topup_remaining_changed(self, value):
        self.values_dict['topup_remaining'] = value
        self.update_values()
        # self.logger.debug('New top-up remaining time=%ss' % value)

    def update_values(self):
        values_to_send = list()
        values_to_send.append(self.values_dict['mach_current'])
        values_to_send.append(self.values_dict['mach_status'])
        values_to_send.append(self.values_dict['topup_remaining'])

        self.emit('valuesChanged', values_to_send)
        # self.logger.debug("SIGNAL valuesChanged emitted")

    def get_mach_current(self):
        value = None
        try:
            value = self.chan_mach_current.get_value()
        except Exception as e:
            self.logger.error('Cannot read machine current value.\n%s' % str(e))
        finally:
            return value

    def get_current(self):
        return self.get_mach_current()

    def get_message(self):
        return 'Machine info status: %s' % str(self.get_mach_status()).split('.')[-1]

    def get_mach_status(self):
        return self.chan_mach_status.get_value()

    def get_topup_remaining(self):
        return self.chan_topup_remaining.get_value()


def test_hwo(hwo):
    print(hwo.get_message())
    print("Current = %s" % hwo.get_current())
    print("Top-Up remaining = %s" % hwo.get_topup_remaining())
