import logging
from HardwareRepository.BaseHardwareObjects import Equipment
import gevent
import time

class CatsMaint(Equipment):
    __TYPE__ = "CATS"    
    NO_OF_LIDS = 3

    """
    Actual implementation of the CATS Sample Changer, MAINTENANCE COMMANDS ONLY
    BESSY BL14.1 installation with 3 lids and 90 samples
    """    
    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)
            
    def init(self):      
        self._chnPathRunning = self.getChannelObject("_chnPathRunning")
        self._chnPathRunning.connectSignal("update", self._updateRunningState)
           
        for command_name in ("_cmdReset", "_cmdBack", "_cmdSafe", "_cmdPowerOn", "_cmdPowerOff", \
                             "_cmdOpenLid1", "_cmdCloseLid1", "_cmdOpenLid2", "_cmdCloseLid2", "_cmdOpenLid3", "_cmdCloseLid3"):
            setattr(self, command_name, self.getCommandObject(command_name))

        for lid_index in range(CatsMaint.NO_OF_LIDS):            
            channel_name = "_chnLid%dState" % (lid_index + 1)
            setattr(self, channel_name, self.getChannelObject(channel_name))
            if getattr(self, channel_name) is not None:
                getattr(self, channel_name).connectSignal("update", getattr(self, "_updateLid%dState" % (lid_index + 1)))

    ################################################################################

    def _doAbort(self):
        self._cmdAbort()            

    def _doReset(self):
        self._cmdReset()

    def _doBack(self):
        argin = 2
        self._executeServerTask(self._cmdBack, argin)

    def _doSafe(self):
        argin = 2
        self._executeServerTask(self._cmdSafe, argin)

    def _doPowerState(self, state=False):
        if state:
            self._cmdPowerOn()
        else:
            self._cmdPowerOff()

    def _doLid1State(self, state = True):
        if state:
            self._executeServerTask(self._cmdOpenLid1)
        else:
            self._executeServerTask(self._cmdCloseLid1)
           
    def _doLid2State(self, state = True):
        if state:
            self._executeServerTask(self._cmdOpenLid2)
        else:
            self._executeServerTask(self._cmdCloseLid2)
           
    def _doLid3State(self, state = True):
        if state:
            self._executeServerTask(self._cmdOpenLid3)
        else:
            self._executeServerTask(self._cmdCloseLid3)
           
    #########################           PRIVATE           #########################        

    def _updateRunningState(self, value):
        self.emit('runningStateChanged', (value, ))

    def _updateLid1State(self, value):
        self.emit('lid1StateChanged', (value, ))

    def _updateLid2State(self, value):
        self.emit('lid2StateChanged', (value, ))

    def _updateLid3State(self, value):
        self.emit('lid3StateChanged', (value, ))

    def _updateOperationMode(self, value):
        self._scIsCharging = not value

    def _executeServerTask(self, method, *args):
        task_id = method(*args)
        print "CatsMaint._executeServerTask", task_id
        ret=None
        # introduced wait because it takes some time before the attribute PathRunning is set
        # after launching a transfer
        time.sleep(2.0)
        while str(self._chnPathRunning.getValue()).lower() == 'true': 
            gevent.sleep(0.1)            
        ret = True
        return ret

