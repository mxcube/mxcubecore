import logging
from gevent import spawn_later
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLPPUControl(Device):    

    def __init__(self, name):
        Device.__init__(self, name)	

        self.status_result = None
        self.restart_result = None

        self.error_state = None
        self.is_error = False

        self.cmd_all_status = None
        self.cmd_furka_restart = None
        self.cmd_all_restart = None

        self.msg = ""
      
        self.status_running = None
        self.restart_running = None
	
    def init(self):
        self.status_result = ""
        self.restart_result = ""
        self.execution_state = self.getProperty("executionState")
        self.error_state = self.getProperty("errorState")

        self.cmd_all_status = self.getCommandObject('cmdAllStatus')
        self.chan_all_status = self.getChannelObject('chanAllStatus')

        self.cmd_all_restart = self.getCommandObject('cmdAllRestart')
        self.cmd_furka_restart = self.getCommandObject('cmdFurkaRestart') 
        self.cmd_furka_restart("")

        self.get_status()
   
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
        """
        self.update_counter = self.update_counter + 1
        print "self.update_counter", self.update_counter
        print status
        """
        if self.status_running and not status: 
           self.all_status = self.cmd_all_status.get() #status
           self.update_status()
        self.status_running = status

    def all_restart_changed(self, status):
        if self.restart_running and not status:
           self.restart_result = self.cmd_all_restart.get() #status
        self.restart_running = status

    def get_status(self):
        self.cmd_all_status("")

    def update_status(self):
        """ 
        if self.update_counter <= 2: #self.at_startup:
            #print 'BBBBBBBBBB at startup'
            #print self.all_status 
            self.at_startup = False
            return

        

        if self.execution_state in self.all_status:
	    #print 'AAAA', self.at_startup, self.all_status
            return

        #print 'CCCCCCC'
        #print self.all_status
        #print self.execution_state
        """
        self.is_error = self.all_status.startswith(self.error_state)

        if self.is_error:
            msg_list = self.all_status.split("\n")
            logging.getLogger("user_level_log").error("PPU control is in Error state!")
            if len(msg_list) > 1:
                for msg_line in msg_list:
                    if msg_line:
                        logging.getLogger("user_level_log").error("PPU control: %s" % msg_line)
        else:
            logging.getLogger("HWR").debug("PPUControl: %s" % \
                   self.all_status)

        self.msg = "Restart result:\n\n%s\n\n" % self.restart_result + \
                   "All status result:\n\n%s" % self.all_status 

        self.emit('ppuStatusChanged', self.is_error, self.msg)

        return self.is_error, self.all_status

    def restart_all(self):
        self.emit('ppuStatusChanged', False,"Restarting.... ")
        self.cmd_all_restart("")
        self.get_status()

    def update_values(self):
        self.emit('ppuStatusChanged', self.is_error, self.msg)
