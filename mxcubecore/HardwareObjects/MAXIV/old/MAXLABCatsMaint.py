"""
CATS maintenance commands hardware object.

Functionality in addition to sample-transfer functionality: power control,
lid control, error-recovery commands, ...
Derived from Michael Hellmig's implementation for the BESSY CATS sample changer
 -add more controls, including Regulation Off, Gripper Dry/Open/Close, Reset Memory, Set Sample On Diff
 -add CATS dewar layout
"""
import logging
from HardwareRepository.TaskUtils import task
from HardwareRepository.BaseHardwareObjects import Equipment
import gevent
import time
import MAXLABCats90

__author__ = "Jie Nan"
__credits__ = ["The MxCuBE collaboration"]

__email__ = "jie.nan@maxlab.lu.se"
__status__ = "Alpha"


class MAXLABCatsMaint(Equipment):
    __TYPE__ = "CATS"
    NO_OF_LIDS = 3

    """
    Actual implementation of the CATS Sample Changer, MAINTENANCE COMMANDS ONLY
    BESSY BL14.1 installation with 3 lids
    """

    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        self._chnPathRunning = self.getChannelObject("_chnPathRunning")
        self._chnPathRunning.connectSignal("update", self._updateRunningState)
        self._chnPowered = self.getChannelObject("_chnPowered")
        self._chnPowered.connectSignal("update", self._updatePoweredState)
        self._chnToolOpenClose = self.getChannelObject("_chnToolOpenClose")
        self._chnToolOpenClose.connectSignal("update", self._updateToolState)
        self._chnMessage = self.getChannelObject("_chnMessage")
        self._chnMessage.connectSignal("update", self._updateMessage)
        self._chnLN2Regulation = self.getChannelObject("_chnLN2RegulationDewar1")
        self._chnLN2Regulation.connectSignal("update", self._updateRegulationState)

        for command_name in (
            "_cmdReset",
            "_cmdDry",
            "_cmdOpenTool",
            "_cmdCloseTool",
            "_cmdCalibration",
            "_cmdSetOnDiff",
            "_cmdClearMemory",
            "_cmdResetParameters",
            "_cmdBack",
            "_cmdSafe",
            "_cmdPowerOn",
            "_cmdPowerOff",
            "_cmdOpenLid1",
            "_cmdCloseLid1",
            "_cmdOpenLid2",
            "_cmdCloseLid2",
            "_cmdOpenLid3",
            "_cmdCloseLid3",
            "_cmdRegulOn",
        ):
            setattr(self, command_name, self.getCommandObject(command_name))

        for lid_index in range(self.NO_OF_LIDS):
            channel_name = "_chnLid%dState" % (lid_index + 1)
            setattr(self, channel_name, self.getChannelObject(channel_name))
            if getattr(self, channel_name) is not None:
                getattr(self, channel_name).connectSignal(
                    "update", getattr(self, "_updateLid%dState" % (lid_index + 1))
                )

    ################################################################################

    def backTraj(self):
        """
        Moves a sample from the gripper back into the dewar to its logged position.
        """
        return self._executeTask(False, self._doBack)

    def safeTraj(self):
        """
        Safely Moves the robot arm and the gripper to the home position
        """
        return self._executeTask(False, self._doSafe)

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

    def _doResetMemory(self):
        """
        Launch the "reset memory" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdClearMemory()
        time.sleep(1)
        self._cmdResetParameters()
        time.sleep(1)

    def _doCalibration(self):
        """
        Launch the "toolcalibration" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdCalibration(2)

    def _doOpenTool(self):
        """
        Launch the "opentool" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdOpenTool()

    def _doCloseTool(self):
        """
        Launch the "closetool" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdCloseTool()

    def _doDryGripper(self):
        """
        Launch the "dry" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdDry(2)

    def _doSetOnDiff(self, sample):
        """
        Launch the "setondiff" command on the CATS Tango DS, an example of sample value is 2:05

        :returns: None
        :rtype: None
        """

        if sample is None:
            raise Exception("No sample selected")
        else:
            str_tmp = str(sample)
            sample_tmp = str_tmp.split(":")
            # calculate CATS specific lid/sample number
            lid = (int(sample_tmp[0]) - 1) / 3 + 1
            puc_pos = ((int(sample_tmp[0]) - 1) % 3) * 10 + int(sample_tmp[1])
            argin = [str(lid), str(puc_pos), "0"]
            logging.getLogger().info("to SetOnDiff %s", argin)
            self._executeServerTask(self._cmdSetOnDiff, argin)

    def _doBack(self):
        """
        Launch the "back" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = ["2", "0"]  # to send string array with two arg...
        self._executeServerTask(self._cmdBack, argin)

    def _doSafe(self):
        """
        Launch the "safe" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = 2
        self._executeServerTask(self._cmdSafe, argin)

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

    def _doDisableRegulation(self):
        """
        Switch off CATS regulation

        :returns: None
        :rtype: None
        """
        self._cmdRegulOff()

    def _doLid1State(self, state=True):
        """
        Opens lid 1 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._executeServerTask(self._cmdOpenLid1)
        else:
            self._executeServerTask(self._cmdCloseLid1)

    def _doLid2State(self, state=True):
        """
        Opens lid 2 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._executeServerTask(self._cmdOpenLid2)
        else:
            self._executeServerTask(self._cmdCloseLid2)

    def _doLid3State(self, state=True):
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

    def _executeTask(self, wait, method, *args):
        ret = self._run(method, wait=False, *args)
        if wait:
            return ret.get()
        else:
            return ret

    @task
    def _run(self, method, *args):
        exception = None
        ret = None
        try:
            ret = method(*args)
        except Exception as ex:
            exception = ex
        if exception is not None:
            raise exception
        return ret

    #########################           PRIVATE           #########################

    def _updateRunningState(self, value):
        self.emit("runningStateChanged", (value,))

    def _updatePoweredState(self, value):
        self.emit("powerStateChanged", (value,))

    def _updateToolState(self, value):
        self.emit("toolStateChanged", (value,))

    def _updateMessage(self, value):
        self.emit("messageChanged", (value,))

    def _updateRegulationState(self, value):
        self.emit("regulationStateChanged", (value,))

    def _updateLid1State(self, value):
        self.emit("lid1StateChanged", (value,))

    def _updateLid2State(self, value):
        self.emit("lid2StateChanged", (value,))

    def _updateLid3State(self, value):
        self.emit("lid3StateChanged", (value,))

    def _updateOperationMode(self, value):
        self._scIsCharging = not value

    def _executeServerTask(self, method, *args):
        task_id = method(*args)
        print "CatsMaint._executeServerTask", task_id
        ret = None
        # introduced wait because it takes some time before the attribute PathRunning is set
        # after launching a transfer
        # after setting refresh in the Tango DS to 0.1 s a wait of 1s is enough
        time.sleep(1.0)
        while str(self._chnPathRunning.getValue()).lower() == "true":
            gevent.sleep(0.1)
        ret = True
        return ret
