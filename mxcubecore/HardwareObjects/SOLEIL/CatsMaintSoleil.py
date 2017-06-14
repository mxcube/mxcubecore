"""
CATS maintenance commands hardware object.

Functionality in addition to sample-transfer functionality: power control,
lid control, error-recovery commands, ...
"""
import logging
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import Equipment
import gevent
import time

__author__ = "Michael Hellmig"
__credits__ = ["The MxCuBE collaboration"]

__email__ = "michael.hellmig@helmholtz-berlin.de"
__status__ = "Beta"

class CatsMaintSoleil(Equipment):
    __TYPE__ = "CATS"    
    NO_OF_LIDS = 3

    """
    Actual implementation of the CATS Sample Changer, MAINTENANCE COMMANDS ONLY
    BESSY BL14.1 installation with 3 lids
    """    
    def __init__(self, *args, **kwargs):
        logging.info('CatsMaint: __init__')
        Equipment.__init__(self, *args, **kwargs)
            
    def init(self):
        logging.info('CatsMaint: init')
        self._chnPathRunning = self.getChannelObject("_chnPathRunning")
        self._chnPathRunning.connectSignal("update", self._updateRunningState)
        self._chnPowered = self.getChannelObject("_chnPowered")
        self._chnPowered.connectSignal("update", self._updatePoweredState)
        self._chnMessage = self.getChannelObject("_chnMessage")
        self._chnMessage.connectSignal("update", self._updateMessage)
        self._chnLN2Regulation = self.getChannelObject("_chnLN2RegulationDewar1")
        self._chnLN2Regulation.connectSignal("update", self._updateRegulationState)
        logging.info('self._chnPathRunning %s' % self._chnPathRunning)
        for command_name in ("_cmdReset", "_cmdBack", "_cmdSafe", "_cmdHome", "_cmdDry", "_cmdDrySoak", "_cmdSoak", "_cmdClearMemory",\
                             "_cmdAckSampleMemory", "_cmdOpenTool", "_cmdToolCal", "_cmdPowerOn", "_cmdPowerOff", \
                             "_cmdOpenLid1", "_cmdCloseLid1", "_cmdOpenLid2", "_cmdCloseLid2", "_cmdOpenLid3", "_cmdCloseLid3", \
                             "_cmdRegulOn"):
            setattr(self, command_name, self.getCommandObject(command_name))

        for lid_index in range(self.NO_OF_LIDS):            
            channel_name = "_chnLid%dState" % (lid_index + 1)
            setattr(self, channel_name, self.getChannelObject(channel_name))
            if getattr(self, channel_name) is not None:
                getattr(self, channel_name).connectSignal("update", getattr(self, "_updateLid%dState" % (lid_index + 1)))

    ################################################################################

    def backTraj(self):    
        """
        Moves a sample from the gripper back into the dewar to its logged position.
        """    
        return self._executeTask(False,self._doBack)     

    def safeTraj(self):    
        """
        Safely Moves the robot arm and the gripper to the home position
        """    
        return self._executeTask(False,self._doSafe)     

    ###MS 2014-11-18
    def homeTraj(self):    
        """
        Moves the robot arm to the home position
        """    
        return self._executeTask(False,self._doHome)  
        
    def dryTraj(self):    
        """
        Drying the gripper
        """    
        return self._executeTask(False,self._doDry)  
        
    def drySoakTraj(self):    
        """
        Dry and Soak the gripper
        """    
        return self._executeTask(False,self._doDrySoak)
        
    def soakTraj(self):    
        """
        Soaking the gripper
        """    
        return self._executeTask(False,self._doSoak)  
        
    def clearMemory(self):    
        """
        Clears the memory
        """    
        return self._executeTask(False,self._doClearMemory)  
    
    def ackSampleMemory(self):    
        """
        Acknowledge incoherence between memorized and actual sample status -- e.g. if robot executed put trajectory but no sample was mounted on the gonio -- either because of empty position or problem with gripper.
        """    
        return self._executeTask(False,self._doAckSampleMemory) 
        
    def opentool(self):    
        """
        Drying the gripper
        """    
        return self._executeTask(False,self._doOpentool)  
        
    def toolcalTraj(self):    
        """
        Soaking the gripper
        """    
        return self._executeTask(False,self._doToolCal)  
    ###
    
    def _doAbort(self):
        """
        Launch the "abort" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdAbort()            

    def _doReset(self):
        """
        Launch the "reset" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdReset()

    def _doBack(self):
        """
        Launch the "back" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 1
        self._executeServerTask(self._cmdBack, argin)

    def _doSafe(self):
        """
        Launch the "safe" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 1
        self._executeServerTask(self._cmdSafe, argin)

    # MS 2014-11-18
    def _doHome(self):
        """
        Launch the "home" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 1
        self._executeServerTask(self._cmdHome, argin)
    
    def _doDry(self):
        """
        Launch the "dry" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 1
        self._executeServerTask(self._cmdDry, argin)
    
    def _doDrySoak(self):
        """
        Launch the "dry_soak" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = ('1', '2')
        self._executeServerTask(self._cmdDrySoak, argin)
        
    def _doSoak(self):
        """
        Launch the "soak" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = ('1', '2')
        self._executeServerTask(self._cmdSoak, argin)
        
    def _doClearMemory(self):
        """
        Execute "clear_memory" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        #argin = 1
        self._executeServerTask(self._cmdClearMemory)
        
    def _doAckSampleMemory(self):
        """
        Execute "clear_memory" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        #argin = 1
        self._executeServerTask(self._cmdAckSampleMemory)
    
    def _doOpentool(self):
        """
        Open tool via the CATS Tango DS

        :returns: None
        :rtype: None
        """
        #argin = 1
        self._executeServerTask(self._cmdOpenTool) #, argin)
        
    def _doToolCal(self):
        """
        Launch the "toolcal" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        #argin = 1
        self._executeServerTask(self._cmdToolCal)     
    ###
    
    def _doPowerState(self, state=False):
        """
        Switch on CATS power if >state< == True, power off otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._cmdPowerOn()
        else:
            self._cmdPowerOff()

    def _doEnableRegulation(self):
        """
        Switch on CATS regulation

        :returns: None
        :rtype: None
        """
        self._cmdRegulOn()

    def _doLid1State(self, state = True):
        """
        Opens lid 1 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._executeServerTask(self._cmdOpenLid1)
        else:
            self._executeServerTask(self._cmdCloseLid1)
           
    def _doLid2State(self, state = True):
        """
        Opens lid 2 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._executeServerTask(self._cmdOpenLid2)
        else:
            self._executeServerTask(self._cmdCloseLid2)
           
    def _doLid3State(self, state = True):
        """
        Opens lid 3 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._executeServerTask(self._cmdOpenLid3)
        else:
            self._executeServerTask(self._cmdCloseLid3)
           
    #########################          PROTECTED          #########################        

    def _executeTask(self,wait,method,*args):        
        ret= self._run(method,wait=False,*args)
        if (wait):                        
            return ret.get()
        else:
            return ret    
        
    @task
    def _run(self,method,*args):
        exception=None
        ret=None    
        try:            
            ret=method(*args)
        except Exception as ex:        
            exception=ex
        if exception is not None:
            raise exception
        return ret

    #########################           PRIVATE           #########################        

    def _updateRunningState(self, value):
        logging.info('CatsMaint _updateRunningState %s' % value)
        self.emit('runningStateChanged', (value, ))

    def _updatePoweredState(self, value):
        logging.info('CatsMaint _updatePoweredState %s' % value)
        self.emit('powerStateChanged', (value, ))

    def _updateMessage(self, value):
        logging.info('CatsMaint _updateMessage %s' % value)
        if 'incoherent' in value.lower():
            value = '%s\nThe sample is not present on the gonio although robot thinks it should be.\nThis can happen in three cases:\n1. there was no sample in the specified position in the puck,\n2. the robot could not get it (rare)\n3. the gonio can not detect sample which is present (very rare).\nIf the sample is really not present on the gonio please click "abort" button\n and then "Missing sample" button below to be able to continue.' % value
        if 'trfgtd' in value.lower():
            value = '%s\nTransfer permission was not granted by the gonio.\n1. Please Abort the trajectory\n2. set gonio to Transfer phase from the pull down menu on the right\n3. Start the load/unload trajectory again.' % value
        if 'dback' in value.lower():
            value = '%s\nThe detector is too close (less then 180 mm from the sample)\nPlease move it to at least 181 mm.' % value
        if 'remote mode requested' in value.lower():
            value = '%s\nRemote operation not enabled.\nPlease turn the robot key to the remote position.\nThe key is located next to the experiment hutch door.' % value
        self.emit('messageChanged', (value, ))

    def _updateRegulationState(self, value):
        logging.info('CatsMaint _updateRegulationState %s' % value)
        self.emit('regulationStateChanged', (value, ))

    def _updateLid1State(self, value):
        logging.info('CatsMaint _updateLid1State %s' % value)
        self.emit('lid1StateChanged', (value, ))

    def _updateLid2State(self, value):
        logging.info('CatsMaint _updateLid2State %s' % value)
        self.emit('lid2StateChanged', (value, ))

    def _updateLid3State(self, value):
        logging.info('CatsMaint _updateLid3State %s' % value)
        self.emit('lid3StateChanged', (value, ))

    def _updateOperationMode(self, value):
        self._scIsCharging = not value

    def _executeServerTask(self, method, *args):
        task_id = method(*args)
        print "CatsMaint._executeServerTask", task_id
        ret=None
        # introduced wait because it takes some time before the attribute PathRunning is set
        # after launching a transfer
        # after setting refresh in the Tango DS to 0.1 s a wait of 1s is enough
        time.sleep(1.0)
        while str(self._chnPathRunning.getValue()).lower() == 'true': 
            gevent.sleep(0.1)            
        ret = True
        return ret

