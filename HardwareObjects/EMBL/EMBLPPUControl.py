import logging
from gevent import spawn_later
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLPPUControl(Device):    

    def __init__(self, name):
        Device.__init__(self, name)

        self.all_status = None
        self.status_result = None
        self.restart_result = None

        self.error_state = None
        self.is_error = False
        self.file_transfer_in_error = False

        self.cmd_all_status = None
        self.cmd_furka_restart = None
        self.cmd_all_restart = None

        self.msg = ""
      
        self.status_running = None
        self.restart_running = None

    def init(self):
        self.all_status = ""
        self.status_result = ""
        self.restart_result = ""
        self.execution_state = self.getProperty("executionState")
        self.error_state = self.getProperty("errorState")

        self.chan_all_status = self.getChannelObject('chanAllStatus')

        self.cmd_all_status = self.getCommandObject('cmdAllStatus')
        self.cmd_all_restart = self.getCommandObject('cmdAllRestart')
        self.cmd_furka_restart = self.getCommandObject('cmdFurkaRestart') 
        self.cmd_furka_restart("")

        self.get_status()

        self.chan_file_info = self.getChannelObject('chanFileInfo')
        if self.chan_file_info is not None:
            self.chan_file_info.connectSignal('update', self.file_info_changed)
   
        #self.update_counter = 0

        #self.at_startup = True
        self.connect(self.chan_all_status,
                     "update",
                     self.all_status_changed)

        self.chan_all_restart = self.getChannelObject('chanAllRestart')
        self.connect(self.chan_all_restart,
                     "update",
                     self.all_restart_changed)

    def all_status_changed(self, status):
        if self.status_running and not status: 
           self.all_status = self.cmd_all_status.get() #status
           self.update_status()
        self.status_running = status

    def all_restart_changed(self, status):
        if self.restart_running and not status:
           self.restart_result = self.cmd_all_restart.get() #status
        self.restart_running = status

    def file_info_changed(self, value):
        if len(value) == 2:
            values = value[1]
        else:
            values = value[0]
         
        self.file_transfer_in_error = values[2] > 0
        self.emit("fileTranferStatusChanged", (values))

        self.is_error = self.all_status.startswith(self.error_state) or \
                        self.file_transfer_in_error

        if self.file_transfer_in_error:
            self.emit('ppuStatusChanged', self.is_error, "File tansfer in error")

    def get_status(self):
        self.cmd_all_status("")

    def update_status(self):
        self.is_error = self.all_status.startswith(self.error_state) or \
                        self.file_transfer_in_error

        if self.all_status.startswith(self.error_state):
            msg_list = self.all_status.split("\n")
            logging.getLogger("GUI").error("PPU control is in Error state!")
            if len(msg_list) > 1:
                for msg_line in msg_list:
                    if msg_line:
                        logging.getLogger("GUI").error("PPU control: %s" % msg_line)
        else:
            logging.getLogger("HWR").debug("PPUControl: %s" % \
                   self.all_status)

        self.msg = "Restart result:\n\n%s\n\n" % self.restart_result + \
                   "All status result:\n\n%s\n" % self.all_status

        self.emit('ppuStatusChanged', self.is_error, self.msg)

        return self.is_error, self.all_status

    def restart_all(self):
        self.emit('ppuStatusChanged', False,"Restarting.... ")
        self.cmd_all_restart("")
        self.get_status()

    def update_values(self):
        self.emit('ppuStatusChanged', self.is_error, self.msg)
