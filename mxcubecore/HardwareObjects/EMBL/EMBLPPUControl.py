import logging
from gevent import spawn_later
from HardwareRepository.BaseHardwareObjects import Device


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLPPUControl(Device):    
    """
    Descript. :
    """  
    def __init__(self, name):
        """
        Descript. :
        """ 
        Device.__init__(self, name)	
        self.status_result = None
        self.restart_result = None
        self.last_resort_result = None
        self.execution_state = None
        self.error_state = None
        self.is_error = None

        self.cmd_furka_restart = None
        self.cmd_all_status = None
        self.cmd_all_restart = None
	
    def init(self):
        """
        Descript. :
        """

        self.status_result = ""
        self.restart_result = ""
        self.last_resort_result = ""

        self.emit('ppuStatusChanged', (True, "hwobj init...."))

        self.cmd_furka_restart = self.getCommandObject('furkaRestart')
        if self.cmd_furka_restart is not None:
            self.cmd_furka_restart.connectSignal('commandReplyArrived', \
                 self.restart_reply)
            try:
                self.cmd_furka_restart("")
            except:
                logging.getLogger("HWR").error("PPUControl: Unable to send " +\
                   "Furka restard command")

        self.cmd_all_status = self.getCommandObject('allStatus')
        if self.cmd_all_status is not None:
            #self.cmd_all_status.connectSignal('commandReplyArrived', \
            #     self.status_reply)
            pass

        self.cmd_all_restart = self.getCommandObject('allRestart')
        if self.cmd_all_restart is not None:
            self.cmd_all_restart.connectSignal('commandReplyArrived', \
                 self.restart_all_reply)

        self.execution_state = self.getProperty("executionState")
        self.error_state = self.getProperty("errorState")

        try:
            self.restart_reply_cb()
        except:
            logging.getLogger("HWR").error("PPUControl: Unable to send " +\
                "Furka restart command")

    def restart_reply_cb(self):
        """
        Descript. :
        """
        self.restart_result = self.cmd_furka_restart.get()
        if ((self.restart_result == self.execution_state) or
            (self.restart_result is None)):
            spawn_later(1, self.restart_reply_cb)
            #QTimer.singleShot(1000, self.restart_reply_cb)
        else:
            if (self.restart_result.startswith(self.error_state)):
                logging.getLogger("HWR").error("PPUControl: %s" % \
                        self.restart_result)
            else:
                logging.getLogger("HWR").debug("PPUControl: %s" % \
                        self.restart_result)
            self.get_status()

    def status_reply_cb(self):
        """
        Descript. :
        """
        status_result = self.cmd_all_status.get()
        if ((status_result == self.execution_state) or
            (status_result is None)):
            spawn_later(1, self.status_reply_cb)
        else:
            self.status_result = status_result
            self.is_error = self.status_result.startswith(self.error_state)
            self.emit('ppuStatusChanged', (self.is_error, self.status_result))
            if self.is_error:
                logging.getLogger("HWR").error("PPUControl: %s" % \
                        self.status_result)
            else:
                logging.getLogger("HWR").debug("PPUControl: %s" % \
                        self.status_result)

    def last_resort_reply_cb(self):
        """
        Descript. :
        """
        last_resort_result = self.cmd_all_restart.get()
        if ((last_resort_result == self.execution_state) or
            (last_resort_result is None)):
            spawn_later(1, self.last_resort_reply_cb)
        else:
            self.last_resort_result = last_resort_result
            self.is_error = self.last_resort_result.startswith(self.error_state)
            self.emit('ppuStatusChanged', (self.is_error, self.last_resort_result))
            if self.is_error:
                logging.getLogger("HWR").error("PPUControl: %s" % \
                        self.last_resort_result)
            else:
                logging.getLogger("HWR").debug("PPUControl: %s" % \
                        self.last_resort_result)  

    def restart_reply(self, result, temp):
        """
        Descript. :
        """
        self.restart_result = result

    def get_restart_reply(self):
        """
        Descript. :
        """
        return self.restart_result

    def status_reply(self, result, temp):
        """
        Descript. :
        """
        self.status_result = result

    def get_status_reply(self):
        """
        Descript. :
        """
        return self.status_result 

    def restart_all_reply(self, result, temp):
        """
        Descript. :
        """ 
        self.last_resort_result = result

    def get_restart_all_reply(self):
        """
        Descript. :
        """
        return self.last_resort_result 

    def get_status(self):
        """
        Descript. :
        """
        self.cmd_all_status("")
        self.status_reply_cb()
        return self.is_error, self.status_result

    def restart_all(self):
        """
        Descript. :
        """
        self.cmd_all_restart("")
        self.last_resort_reply_cb()

    def update_values(self):
        self.emit('ppuStatusChanged', (self.is_error, self.last_resort_result))
