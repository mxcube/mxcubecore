import logging
import time
import gevent
from gevent import monkey
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.TaskUtils import task
from HardwareRepository.CommandContainer import CommandObject
from HardwareRepository import HardwareRepository as HWR

monkey.patch_all(thread=False)


class ControllerCommand(CommandObject):
    def __init__(self, name, cmd):
        CommandObject.__init__(self, name)
        self._cmd = cmd
        self._cmd_execution = None
        self.type = "CONTROLLER"

    def isConnected(self):
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
            except BaseException:
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


class BIOMAXBeamlineActions(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def _prepare_open_hutch_task(self):
        """
        Descript.: prepare beamline for openning the hutch door,
        """
        logging.getLogger("HWR").info("Preparing experimental hutch for door openning.")
        time.sleep(1)
        if (
            HWR.beamline.safety_shutter is not None
            and HWR.beamline.safety_shutter.getShutterState() == "opened"
        ):
            logging.getLogger("HWR").info("Closing safety shutter...")
            HWR.beamline.safety_shutter.closeShutter()
            while HWR.beamline.safety_shutter.getShutterState() == "opened":
                gevent.sleep(0.1)

        if self.detector_cover_hwobj is not None:
            logging.getLogger("HWR").info("Closing detector cover...")
            self.detector_cover_hwobj.closeShutter()

        if HWR.beamline.detector.distance is not None:
            logging.getLogger("HWR").info("Moving detector to safe area...")
            HWR.beamline.detector.distance.set_value(800, timeout=50)

        if HWR.beamline.sample_changer.is_powered():
            if HWR.beamline.sample_changer.get_loaded_sample() is not None:
                logging.getLogger("HWR").info("Unloading mounted sample.")
                HWR.beamline.sample_changer.unload(None, wait=True)
                HWR.beamline.sample_changer._wait_device_ready(30)
            if HWR.beamline.sample_changer._chnInSoak.getValue():
                logging.getLogger("HWR").info(
                    "Sample Changer was in SOAK, going to DRY"
                )
                self.sample_changer_maint_hwobj.send_command("dry")
                gevent.sleep(1)
                HWR.beamline.sample_changer._wait_device_ready(300)
            if HWR.beamline.sample_changer.is_powered():
                logging.getLogger("HWR").info("Sample Changer to HOME")
                self.sample_changer_maint_hwobj.send_command("home")
                gevent.sleep(1)
                HWR.beamline.sample_changer._wait_device_ready(30)

                logging.getLogger("HWR").info("Sample Changer CLOSING LID")
                self.sample_changer_maint_hwobj.send_command("closelid1")
                gevent.sleep(1)
                HWR.beamline.sample_changer._wait_device_ready(10)

                logging.getLogger("HWR").info("Sample Changer POWER OFF")
                self.sample_changer_maint_hwobj.send_command("powerOff")
        else:
            logging.getLogger("HWR").warning(
                "Cannot prepare Hutch openning, Isara is powered off"
            )

    def _prepare_for_new_sample_task(self, manual_mode=True):
        """
        Descript.: prepare beamline for a new sample,
        """
        logging.getLogger("HWR").info("Preparing beamline for a new sample.")
        time.sleep(1)
        if manual_mode:
            if self.detector_cover_hwobj is not None:
                logging.getLogger("HWR").info("Closing detector shutter...")
                self.detector_cover_hwobj.closeShutter()
            logging.getLogger("HWR").info("Setting diffractometer in Transfer phase...")
            HWR.beamline.diffractometer.set_phase("Transfer", wait=False)

            if (
                HWR.beamline.safety_shutter is not None
                and HWR.beamline.safety_shutter.getShutterState() == "opened"
            ):
                logging.getLogger("HWR").info("Closing safety shutter...")
                HWR.beamline.safety_shutter.closeShutter()
                while HWR.beamline.safety_shutter.getShutterState() == "opened":
                    gevent.sleep(0.1)

        if HWR.beamline.detector.distance is not None:
            logging.getLogger("HWR").info("Moving detector to safe area...")
            HWR.beamline.detector.distance.set_value(800, timeout=50)

    def init(self):
        self.sample_changer_maint_hwobj = self.get_object_by_role(
            "sample_changer_maintenance"
        )
        self.detector_cover_hwobj = self.get_object_by_role("detector_cover")

        self.prepare_open_hutch = ControllerCommand(
            "prepare_open_hutch", self._prepare_open_hutch_task
        )
        self.prepare_new_sample = ControllerCommand(
            "prepare_new_sample", self._prepare_for_new_sample_task
        )

    def get_commands(self):
        return [self.prepare_open_hutch, self.prepare_new_sample]
