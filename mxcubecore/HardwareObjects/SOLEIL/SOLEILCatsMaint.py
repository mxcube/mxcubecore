"""
CATS maintenance commands hardware object.

Functionality in addition to sample-transfer functionality: power control,
lid control, error-recovery commands, ...
"""

import logging
from mxcubecore.TaskUtils import task
from mxcubecore.BaseHardwareObjects import HardwareObject
import gevent
import time

__author__ = "Michael Hellmig"
__credits__ = ["The MxCuBE collaboration"]

__email__ = "michael.hellmig@helmholtz-berlin.de"
__status__ = "Beta"


TOOLS = {"FLANGE": 0, "CRYOTONG": 1, "ESRF": 2, "PLATE": 3}


class SOLEILCatsMaint(HardwareObject):

    __TYPE__ = "CATS"

    NO_OF_LIDS = 3

    default_tool = 1
    default_soak_lid = 2

    """
    Actual implementation of the CATS Sample Changer, MAINTENANCE COMMANDS ONLY
    BESSY BL14.1 installation with 3 lids
    """

    def __init__(self, *args, **kwargs):
        logging.info("CatsMaint: __init__")
        super().__init__(*args, **kwargs)

    def init(self):
        logging.info("CatsMaint: init")

        tool = self.get_property("tool")
        if tool in TOOLS:
            self.tool = TOOLS[tool]
        else:
            self.tool = self.default_tool

        soaklid = self.get_property("soak_lid")
        if soaklid is not None:
            self.soaklid = soaklid
        else:
            self.soaklid = self.default_soak_lid

        self.running_safe = False

        self._chnPathRunning = self.get_channel_object("_chnPathRunning")
        self._chnPathRunning.connect_signal("update", self._update_running_state)
        self._chnPowered = self.get_channel_object("_chnPowered")
        self._chnPowered.connect_signal("update", self._update_powered_state)
        self._chnMessage = self.get_channel_object("_chnMessage")
        self._chnMessage.connect_signal("update", self._update_message)
        self._chnLN2Regulation = self.get_channel_object("_chnLN2RegulationDewar1")
        self._chnLN2Regulation.connect_signal("update", self._update_regulation_state)

        for command_name in (
            "_cmdResetError",
            "_cmdBack",
            "_cmdSafe",
            "_cmdHome",
            "_cmdDry",
            "_cmdDrySoak",
            "_cmdSoak",
            "_cmdClearMemory",
            "_cmdAckSampleMemory",
            "_cmdOpenTool",
            "_cmdToolCal",
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
            setattr(self, command_name, self.get_command_object(command_name))

        for lid_index in range(self.NO_OF_LIDS):
            channel_name = "_chnLid%dState" % (lid_index + 1)
            setattr(self, channel_name, self.get_channel_object(channel_name))
            if getattr(self, channel_name) is not None:
                getattr(self, channel_name).connect_signal(
                    "update", getattr(self, "_updateLid%dState" % (lid_index + 1))
                )

    ################################################################################

    def back_traj(self):
        """
        Moves a sample from the gripper back into the dewar to its logged position.
        """
        return self._execute_task(False, self._do_back)

    def safe_traj(self):
        """
        Safely Moves the robot arm and the gripper to the home position
        """
        return self._execute_task(False, self._do_safe)

    # MS 2014-11-18
    def home_traj(self):
        """
        Moves the robot arm to the home position
        """
        return self._execute_task(False, self._do_home)

    def dry_traj(self):
        """
        Drying the gripper
        """
        return self._execute_task(False, self._do_dry)

    def dry_soak_traj(self):
        """
        Dry and Soak the gripper
        """
        return self._execute_task(False, self._do_dry_soak)

    def soak_traj(self):
        """
        Soaking the gripper
        """
        return self._execute_task(False, self._do_soak)

    def integrated_tool_cal(self):
        return self._execute_task(False, self._do_integrated_tool_cal)

    def clear_memory(self):
        """
        Clears the memory
        """
        return self._execute_task(False, self._do_clear_memory)

    def ack_sample_memory(self):
        """
        Acknowledge incoherence between memorized and actual sample status -- e.g. if robot executed put trajectory but no sample was mounted on the gonio -- either because of empty position or problem with gripper.
        """
        return self._execute_task(False, self._do_ack_sample_memory)

    def opentool(self):
        """
        Drying the gripper
        """
        return self._execute_task(False, self._do_opentool)

    def toolcal_traj(self):
        """
        Soaking the gripper
        """
        return self._execute_task(False, self._do_tool_cal)

    ###

    def missingSample(self):
        self._do_ack_sample_memory()
        self._do_clear_memory()
        self._do_resetError()

    def _do_abort(self):
        """
        Launch the "abort" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdAbort()

    def _do_resetError(self):
        """
        Launch the "reset" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdResetError()

    def _do_back(self):
        """
        Launch the "back" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = self.tool
        self._execute_server_task(self._cmdBack, argin)

    def _do_safe(self):
        """
        Launch the "safe" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = self.tool
        self._execute_server_task(self._cmdSafe, argin)

    # MS 2014-11-18
    def _do_home(self):
        """
        Launch the "home" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = self.tool
        self._execute_server_task(self._cmdHome, argin)

    def _do_dry(self):
        """
        Launch the "dry" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = (str(self.tool),)
        self._execute_server_task(self._cmdDry, argin)

    def _do_dry_gripper(self):
        return self._do_dry_soak()

    def _do_dry_soak(self):
        """
        Launch the "dry_soak" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = map(str, (self.tool, self.soaklid))
        self._execute_server_task(self._cmdDrySoak, argin)

    def _do_soak(self):
        """
        Launch the "soak" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = map(str, (self.tool, self.soaklid))
        self._execute_server_task(self._cmdSoak, argin)

    def _do_integrated_tool_cal(self):

        argin = self.tool

        # poweron
        # safe
        # dry
        # tremp_toolcal
        # soak

        self.running_safe = True
        self._update_message("RUNNING Safe process. Phase is: going to Safe")
        logging.getLogger("HWR").info("Executing safe")
        self._execute_server_task(self._cmdSafe, argin, waitstart=True)
        logging.getLogger("HWR").info("Executing safe done")

        self._update_message("RUNNING Safe process. Phase is: Drying")
        logging.getLogger("HWR").info("Executing dry")
        self._execute_server_task(self._cmdDry, argin, waitstart=True)
        logging.getLogger("HWR").info("Executing dry done")

        self._update_message("RUNNING Safe process. Phase is: SoakToolCal")
        logging.getLogger("Executing SoakToolCal")
        self._execute_server_task(self._cmdSoakToolCal, argin, waitstart=True)
        logging.getLogger("Executing SoakToolCal DONE")

        self._update_message("RUNNING Safe process. Phase is: ResetError")
        self._cmdResetError()

        logging.getLogger("Executing SoakToolCal")
        self._update_message(
            "RUNNING Safe process. Phase is: Soak (will take 45 seconds)"
        )
        argin = map(str, (self.tool, self.soaklid))
        self._execute_server_task(self._cmdSoak, argin, waitstart=True)
        logging.getLogger("Executing SoakToolCal done")
        self._update_message("Safe process finished")
        self.running_safe = False

    def _do_clear_memory(self):
        """
        Execute "clear_memory" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        # argin = 1
        self._execute_server_task(self._cmdClearMemory)

    def _do_ack_sample_memory(self):
        """
        Execute "clear_memory" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        # argin = 1
        self._execute_server_task(self._cmdAckSampleMemory)

    def _do_opentool(self):
        """
        Open tool via the CATS Tango DS

        :returns: None
        :rtype: None
        """
        # argin = 1
        self._execute_server_task(self._cmdOpenTool)  # , argin)

    def _do_tool_cal(self):
        """
        Launch the "toolcal" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        # argin = 1
        self._execute_server_task(self._cmdToolCal)

    ###

    def _do_power_state(self, state=False):
        """
        Switch on CATS power if >state< == True, power off otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._cmdPowerOn()
        else:
            self._cmdPowerOff()

    def _do_enable_regulation(self):
        """
        Switch on CATS regulation

        :returns: None
        :rtype: None
        """
        self._cmdRegulOn()

    def _do_lid1_state(self, state=True):
        """
        Opens lid 1 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._execute_server_task(self._cmdOpenLid1)
        else:
            self._execute_server_task(self._cmdCloseLid1)

    def _do_lid2_state(self, state=True):
        """
        Opens lid 2 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._execute_server_task(self._cmdOpenLid2)
        else:
            self._execute_server_task(self._cmdCloseLid2)

    def _do_lid3_state(self, state=True):
        """
        Opens lid 3 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._execute_server_task(self._cmdOpenLid3)
        else:
            self._execute_server_task(self._cmdCloseLid3)

    #########################          PROTECTED          #########################

    def _execute_task(self, wait, method, *args):
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

    def _update_running_state(self, value):
        logging.info("CatsMaint _update_running_state %s" % value)
        self.emit("runningStateChanged", (value,))

    def _update_powered_state(self, value):
        logging.info("CatsMaint _update_powered_state %s" % value)
        self.emit("powerStateChanged", (value,))

    def _update_message(self, value):
        logging.info("CatsMaint _update_message %s" % value)
        if value.strip() == "" and self.running_safe:
            return

        if "incoherent" in value.lower():
            value = (
                '%s\nThe sample is not present on the gonio although robot thinks it should be.\nThis can happen in three cases:\n1. there was no sample in the specified position in the puck,\n2. the robot could not get it (rare)\n3. the gonio can not detect sample which is present (very rare).\nIf the sample is really not present on the gonio please click "abort" button\n and then "Missing sample" button below to be able to continue.'
                % value
            )
        if "trfgtd" in value.lower():
            value = (
                "%s\nTransfer permission was not granted by the gonio.\n1. Please Abort the trajectory\n2. set gonio to Transfer phase from the pull down menu on the right\n3. Start the load/unload trajectory again."
                % value
            )
        if "dback" in value.lower():
            value = (
                "%s\nThe detector is too close (less then 180 mm from the sample)\nPlease move it to at least 181 mm."
                % value
            )
        if "remote mode requested" in value.lower():
            value = (
                "%s\nRemote operation not enabled.\nPlease turn the robot key to the remote position.\nThe key is located next to the experiment hutch door."
                % value
            )
        self.emit("messageChanged", (value,))

    def _update_regulation_state(self, value):
        logging.info("CatsMaint _update_regulation_state %s" % value)
        self.emit("regulationStateChanged", (value,))

    def _update_lid1_state(self, value):
        logging.info("CatsMaint _update_lid1_state %s" % value)
        self.emit("lid1StateChanged", (value,))

    def _update_lid2_state(self, value):
        logging.info("CatsMaint _update_lid2_state %s" % value)
        self.emit("lid2StateChanged", (value,))

    def _update_lid3_state(self, value):
        logging.info("CatsMaint _update_lid3_state %s" % value)
        self.emit("lid3StateChanged", (value,))

    def _update_operation_mode(self, value):
        self._scIsCharging = not value

    def _execute_server_task(self, method, argin=None, waitstart=False):
        if argin is not None:
            task_id = method(argin)
        else:
            task_id = method()

        print("CatsMaint._execute_server_task", task_id)
        ret = None
        # introduced wait because it takes some time before the attribute PathRunning is set
        # after launching a transfer
        # after setting refresh in the Tango DS to 0.1 s a wait of 1s is enough

        if waitstart:
            timeout = 10.0
            t0 = time.time()
            while str(self._chnPathRunning.get_value()).lower() != "true":
                if time.time() - t0 > timeout:
                    logging.getLogger("HWR").info(
                        "Could not detect the start of the task. Continuing"
                    )
                    break
                gevent.sleep(0.1)

        logging.getLogger("HWR").info(
            "server task started. path running %s" % self._chnPathRunning.get_value()
        )
        while str(self._chnPathRunning.get_value()).lower() == "true":
            gevent.sleep(0.1)
        ret = True
        return ret
