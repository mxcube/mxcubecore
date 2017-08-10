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
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import logging
import gevent
from HardwareRepository.BaseHardwareObjects import Device


__version__ = "2.3."
__category__ = "General"


class EMBLSafetyShutter(Device):
    shutter_state_list = {
        3: 'unknown',
        1: 'closed',
        0: 'opened',
        9: 'moving',
        17: 'automatic',
        23: 'fault',
        46: 'disabled',
        -1: 'error'
        }

    def __init__(self, name):
        Device.__init__(self, name)

        self.use_shutter = None
        self.data_collection_state = None
        self.shutter_can_open = None
        self.shutter_state = None
        self.shutter_state_open = None
        self.shutter_can_open = None

        self.chan_collection_state = None
        self.chan_state_open = None
        self.chan_state_open_permission = None

        self.cmd_open = None
        self.cmd_close = None

    def init(self):
        self.chan_collection_state = self.getChannelObject('chanCollectStatus')
        if self.chan_collection_state is not None:
            self.chan_collection_state.connectSignal('update',
                 self.data_collection_state_changed)

        self.chan_state_open = self.getChannelObject('chanStateOpen')
        if self.chan_state_open is not None:
            self.chan_state_open.connectSignal('update',
                 self.state_open_changed)

        self.state_open_changed(self.chan_state_open.getValue())

        self.chan_state_open_permission = self.getChannelObject('chanStateOpenPermission')
        self.chan_state_open_permission.connectSignal('update',
             self.state_open_permission_changed)
        self.state_open_permission_changed(self.chan_state_open_permission.getValue())
         

        self.cmd_open = self.getCommandObject('cmdOpen')
        self.cmd_close = self.getCommandObject('cmdClose')

        self.use_shutter = self.getProperty('useShutter')
        if self.use_shutter is None:
            self.use_shutter = True

        self.getWagoState = self.getShutterState

    def connected(self):
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    def data_collection_state_changed(self, state):
        self.data_collection_state = state
        self.getShutterState()

    def state_open_changed(self, state):
        self.shutter_state_open = state
        self.getShutterState()

    def state_open_permission_changed(self, state):
        self.shutter_can_open = state
        self.getShutterState()

    def getShutterState(self):
        if self.shutter_state_open:
            self.shutter_state = "opened"
        elif self.data_collection_state == "collecting" or not self.shutter_can_open:
            self.shutter_state = "disabled"
        else:
            self.shutter_state = "closed"

        if not self.use_shutter:
            self.shutter_state = self.shutter_state_list[0]

        self.emit('shutterStateChanged', (self.shutter_state,))
        return self.shutter_state

    # set the shutter open command to any TEXT value of size 1 to open it
    def openShutter(self):
        if not self.use_shutter:
            logging.getLogger().info('Safety shutter is disabled')
            return
        self.control_shutter(True)

    # set the shutter close command to any TEXT value of size 1 to open it
    def closeShutter(self):
        self.control_shutter(False)

    def control_shutter(self, open_state):
        if open_state:
            gevent.spawn(self.open_shutter_thread)
        else:
            gevent.spawn(self.close_shutter_thread)

    def close_shutter_thread(self):
        logging.getLogger().info('Safety shutter: Closing beam shutter...')
        #self.emit('shutter_state_listChanged', (self.shutterState[0])) #closed
        gevent.sleep(2)
        try:
            self.cmd_close()
        except:
            logging.getLogger().error('Safety shutter: unable to close shutter')

    def open_shutter_thread(self):
        logging.getLogger().info('Safety shutter: Openning beam shutter...')
        #self.emit('shutter_state_listChanged', (self.shutterState[1])) #opened
        gevent.sleep(2)
        try:
            self.cmd_open()
            """
            gevent.sleep(6)
            if self.getShutterState() != "opened":
                self.cmd_open()
            """
        except:
            logging.getLogger().error('Safety shutter: unable to open shutter')

    def update_values(self):
        self.getShutterState()
