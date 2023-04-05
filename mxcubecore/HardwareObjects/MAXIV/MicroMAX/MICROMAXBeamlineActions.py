import logging
import time
import gevent
import PyTango

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.TaskUtils import task
from mxcubecore.CommandContainer import CommandObject


class ControllerCommand(CommandObject):
    def __init__(self, name, cmd):
        CommandObject.__init__(self, name)
        self._cmd = cmd
        self._cmd_execution = None
        self.type = "CONTROLLER"


    def is_connected(self):
        return True

    def get_arguments(self):
        if self.name() == "Anneal":
            self.add_argument("Time [s]", "float")

        return CommandObject.get_arguments(self)

    @task
    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))
        self._cmd_execution = gevent.spawn(self._cmd, *args, **kwargs)
        self._cmd_execution.link(self._cmd_done)

    def _cmd_done(self, cmd_execution):
        try:
            try:
                res = cmd_execution.get()
            except:
                self.emit("commandFailed", (str(self.name()),))
            else:
                if isinstance(res, gevent.GreenletExit):
                    self.emit("commandFailed", (str(self.name()),))
                else:
                    self.emit("commandReplyArrived", (str(self.name()), res))
        finally:
            self.emit("commandReady")

    def abort(self):
        if self._cmd_execution and not self._cmd_execution.ready():
            self._cmd_execution.kill()

    def value(self):
        return None


class MICROMAXBeamlineActions(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)
        self.command_list = []

    def close_detector_cover(self):
        """
        Descript. :
        """
        try:
            self.log.info("Closing the detector cover")
            plc = PyTango.DeviceProxy('b312a/vac/plc-01')
            plc.B312A_E06_DIA_DETC01_ENAC = 1
            plc.B312A_E06_DIA_DETC01_CLC = 1
        except Exception:
            self.log.exception("Could not close the detector cover")
            pass

    def _prepare_open_hutch_task(self, unmount_sample = False):
        """
        Descript.: prepare beamline for openning the hutch door,
        """
        logging.getLogger("HWR").info("Preparing experimental hutch for door openning.")
        if (
            self.safety_shutter_hwobj is not None
            and self.safety_shutter_hwobj.getShutterState() == "opened"
        ):
            logging.getLogger("HWR").info("Closing safety shutter...")
            self.safety_shutter_hwobj.closeShutter()
            while self.safety_shutter_hwobj.getShutterState() == "opened":
                gevent.sleep(0.1)

        logging.getLogger("HWR").info("Closing detector cover...")
        self.close_detector_cover()

        if self.dtox_hwobj is not None:
            logging.getLogger("HWR").info("Moving detector to safe area...")
            self.dtox_hwobj.sync_move(900, timeout = 50)

    def _end_beamtime(self):
        try:
            self._prepare_open_hutch_task(unmount_sample = True)
            cmd = self.getCommandObject('beamtime_end')
            cmd(wait=True)
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot end beamtime.")

    def _start_beamtime(self):
        try:
            cmd = self.getCommandObject('beamtime_start')
            cmd(wait=True)
            time.sleep(10)
            self._checkbeam()
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot start beamtime.")

    def _open_beamline_shutters(self):
        try:
            cmd = self.getCommandObject('open_beamline_shutters')
            cmd(wait=True)
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot open_beamline_shutters.")

    def init(self):
        self.dtox_hwobj = self.get_object_by_role("dtox")
        self.safety_shutter_hwobj = self.get_object_by_role("safety_shutter")
        self.diffractometer_hwobj = self.get_object_by_role("diffractometer")

        self.prepare_open_hutch = ControllerCommand("prepare_open_hutch", self._prepare_open_hutch_task)
        self.end_beamtime = ControllerCommand("end_beamtime", self._end_beamtime)
        self.open_beamline_shutters = ControllerCommand("open_beamline_shutters", self._open_beamline_shutters)
        self.start_beamtime = ControllerCommand("start_beamtime", self._start_beamtime)

        self.dispatcher = {"prepare_open_hutch": self.prepare_open_hutch,
                           "end_beamtime": self.end_beamtime,
                           "open_beamline_shutters": self.open_beamline_shutters,
                           "start_beamtime": self.start_beamtime }

        self.command_list = eval(self.get_property("command_list"))

    def get_commands(self):
        commands = []
        for command in self.command_list:
            commands.append(self.dispatcher[command])
        return commands

    def get_annotated_commands(self):
        return []
