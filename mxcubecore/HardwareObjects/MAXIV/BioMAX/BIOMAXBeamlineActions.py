import logging
import time
import gevent

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.TaskUtils import task
from mxcubecore.CommandContainer import CommandObject
from mxcubecore import HardwareRepository as HWR


class ControllerCommand(CommandObject):
    def __init__(self, name, cmd):
        CommandObject.__init__(self, name)
        self._cmd = cmd
        self._cmd_execution = None
        self.type = "CONTROLLER"
        if self.name() == 'Anneal':
            self.add_argument("Time [s]", "float")

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


class BIOMAXBeamlineActions(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)
        self.command_list = []

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

        if self.detector_cover_hwobj is not None:
            logging.getLogger("HWR").info("Closing detector cover...")
            self.detector_cover_hwobj.closeShutter()

        if self.dtox_hwobj is not None:
            logging.getLogger("HWR").info("Moving detector to safe area...")
            self.dtox_hwobj.set_value(900, timeout = 50)

        if self.sample_changer_hwobj.isPowered():
            if unmount_sample and self.sample_changer_hwobj.getLoadedSample() is not None:
                logging.getLogger("HWR").info("Unloading mounted sample.")
                self.sample_changer_hwobj.unload(None, wait=True)
                self.sample_changer_hwobj._waitDeviceReady(30)
            if self.sample_changer_hwobj._chnInSoak.getValue():
                logging.getLogger("HWR").info(
                    "Sample Changer was in SOAK, going to DRY"
                )
                self.sample_changer_maint_hwobj.send_command("dry")
            gevent.sleep(1)
            self.sample_changer_hwobj._waitDeviceReady(300)
            if self.sample_changer_hwobj.isPowered():
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
                self.diffractometer_hwobj.set_phase("Transfer", wait=False)
 
            if self.safety_shutter_hwobj is not None and self.safety_shutter_hwobj.getShutterState() == 'opened':
                logging.getLogger("HWR").info("Closing safety shutter...")
                self.safety_shutter_hwobj.closeShutter()
                while self.safety_shutter_hwobj.getShutterState() == 'opened':
                    gevent.sleep(0.1)

        if self.dtox_hwobj is not None:
            logging.getLogger("HWR").info("Moving detector to safe area...")
            self.dtox_hwobj.set_value(800, timeout = 50)

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

    def _calculate_flux(self):
        logging.getLogger("HWR").info("Calculating Flux!")
        self.flux_hwobj.calculate_flux()

    def _checkbeam(self):
        try:
            cmd = self.getCommandObject('checkbeam')
            cmd(wait=True)
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot check beam stability.")

    def _focus_beam_100(self):
        self._focus_beam("100")

    def _focus_beam_50(self):
        self._focus_beam("50")

    def _focus_beam_20(self):
        self._focus_beam("focus")

    def _focus_beam(self, size):
        try:
            cmd = self.getCommandObject('focus_beam')
            cmd(size, wait=True)
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot change beam focus.")


    def _abort_md3(self):
        try:
            self.diffractometer_hwobj.abort()
            omega = self.diffractometer_hwobj.phi_motor_hwobj
            current_state = omega.motors_state_attr.getValue()
            logging.getLogger("HWR").info("Current MD3 omega state is %s" % current_state)
            omega.updateMotorState(current_state)
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot abort MD3")

    def _anneal(self, anneal_time):
        logging.getLogger("HWR").info("Anneal %s" % str(anneal_time))
        try:
            self.diffractometer_hwobj.wait_device_ready(10)
            if anneal_time < 1:
                raise Exception("Time is too short for annealing, set 1s at least.")
            self.diffractometer_hwobj.move_rex_out(wait = False)
            if anneal_time >= 1:
                time.sleep(anneal_time-0.8)
            self.diffractometer_hwobj.move_rex_in(wait = True)
            logging.getLogger("HWR").info("Annealing is done!")
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot anneal the sample")

    def _empty_mount(self):
        if self.diffractometer_hwobj.sample_is_loaded:
            logging.getLogger("HWR").error("Cannot clear sample, there is a sample detected on the goniometer!")
            raise Exception("There is a sample detected on the goniometer!")
        if self.sample_changer_hwobj.isPowered():
            if self.sample_changer_hwobj._chnInSoak.getValue():
                logging.getLogger("HWR").info("Abort Sample Changer")
                self.sample_changer_maint_hwobj.send_command('abort')
                gevent.sleep(2)
                """
                should not wait device ready here, as it will never be ready because there's
                no sample on the diff
                """
                logging.getLogger("HWR").info("Sample Changer: Clear memory")
                self.sample_changer_maint_hwobj.send_command('clear_memory')
                gevent.sleep(1)
                self.sample_changer_hwobj._waitDeviceReady(10)
                self.sample_changer_maint_hwobj._updateGlobalState()
                self.diffractometer_hwobj.last_centered_position = None
            else:
                if self.sample_changer_hwobj._isDeviceReady():
                    logging.getLogger("HWR").error("Doesn't look like an emptry mount, please contact support!")
                else:
                    logging.getLogger("HWR").error("Sample Changer is drying, please wait and try later")
        else:
            logging.getLogger("HWR").error("Sample Changer power is off, please switch it on")

    def _testMacro(self):
        try:
            cmd = self.getCommandObject('testMacro')
            cmd(wait=True)
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot testMacro")

    def _align_beam(self):
        try:
            self.beam_alignment_hwobj.execute_beam_alignment()
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot align beam")

    def _align_aperture(self):
        try:
            self.beam_alignment_hwobj.execute_aperture_alignment()
        except Exception as ex:
            logging.getLogger("HWR").error("Cannot align aperture")

    def _restart_mxcube(self):
        cmd = "sudo systemctl restart mxcube3"
        logging.getLogger("HWR").info("Restarting MXCuBE Server now....this will take ~15s")
        logging.getLogger("HWR").info("Please refresh the page after this")
        time.sleep(2)
        os.system(cmd)

    def _prepare_remove_long_pin(self):
        """
        Descript.: prepare beamline for openning the hutch door to remove long pin,
        """
        logging.getLogger("HWR").info("Preparing experimental hutch for removing long pin.")
        if (
                HWR.beamline.safety_shutter is not None
                and HWR.beamline.safety_shutter.getShutterState() == "opened"
            ):
                logging.getLogger("HWR").info("Closing safety shutter...")
                self.safety_shutter_hwobj.closeShutter()
                while self.safety_shutter_hwobj.getShutterState() == "opened":
                    gevent.sleep(0.1)

        logging.getLogger("HWR").info("Prepare MD3 for removing sample...")
        self.diffractometer_hwobj.set_unmount_sample_phase(wait=False)

        if self.detector_cover_hwobj is not None:
            logging.getLogger("HWR").info("Closing detector cover...")
            self.detector_cover_hwobj.closeShutter()

        if self.dtox_hwobj is not None:
            logging.getLogger("HWR").info("Moving detector to safe area...")
            self.dtox_hwobj.set_value(900, timeout = 50)

    def _check_laser_shutter(self):
        if self.laser_shutter_hwobj is None:
            logging.getLogger("HWR").error("laser shutter is not defined...")
            return
        self.laser_shutter_hwobj.update_state()
        logging.getLogger("HWR").info("laser shutter state is updated: %s " % (self.laser_shutter_hwobj.state_value_str))

    def init(self):
        self.sample_changer_hwobj = self.get_object_by_role("sample_changer")
        self.sample_changer_maint_hwobj = self.get_object_by_role("sample_changer_maintenance")
        self.dtox_hwobj = self.get_object_by_role("dtox")
        self.detector_cover_hwobj = self.get_object_by_role("detector_cover")
        self.safety_shutter_hwobj = self.get_object_by_role("safety_shutter")
        self.diffractometer_hwobj = self.get_object_by_role("diffractometer")
        # self.collect = self.get_object_by_role("collect")
        self.flux_hwobj = self.get_object_by_role("flux")
        self.beam_alignment_hwobj = self.get_object_by_role("beam_alignment")
        self.laser_shutter_hwobj = self.get_object_by_role("laser") or None

        self.prepare_open_hutch = ControllerCommand("prepare_open_hutch", self._prepare_open_hutch_task)
        self.prepare_remove_long_pin = ControllerCommand("prepare_remove_long_pin", self._prepare_remove_long_pin)
        self.prepare_new_sample = ControllerCommand("prepare_new_sample", self._prepare_for_new_sample_task)
        self.end_beamtime = ControllerCommand("end_beamtime", self._end_beamtime)
        self.open_beamline_shutters = ControllerCommand("open_beamline_shutters", self._open_beamline_shutters)
        self.start_beamtime = ControllerCommand("start_beamtime", self._start_beamtime)
        self.calculate_flux = ControllerCommand("calculate_flux", self._calculate_flux)
        self.checkbeam = ControllerCommand("checkbeam", self._checkbeam)
        self.testMacro = ControllerCommand("TestMacro", self._testMacro)
        self.abort_md3 = ControllerCommand("Abort_MD3", self._abort_md3)
        self.restart_mxcube = ControllerCommand("Restart_MXCuBE", self._restart_mxcube)
        self.empty_mount = ControllerCommand("empty_sample_mounted", self._empty_mount)
        self.align_beam = ControllerCommand("Align_beam", self._align_beam)
        self.align_aperture = ControllerCommand("Align_aperture", self._align_aperture)
        self.anneal = ControllerCommand("Anneal", self._anneal)
        self.focus_beam_20 = ControllerCommand("Focus_beam_20x5", self._focus_beam_20)
        self.focus_beam_50 = ControllerCommand("Focus_beam_50x50", self._focus_beam_50)
        self.focus_beam_100 = ControllerCommand("Focus_beam_100x100", self._focus_beam_100)
        self.check_laser_shutter = ControllerCommand("Check_laser_shutter", self._check_laser_shutter)
        self.dispatcher = {"prepare_open_hutch": self.prepare_open_hutch,
                           "prepare_remove_long_pin": self.prepare_remove_long_pin,
                           "end_beamtime": self.end_beamtime,
                           "open_beamline_shutters": self.open_beamline_shutters,
                           "checkbeam": self.checkbeam,
                           "calculate_flux": self.calculate_flux,
                           "align_beam": self.align_beam,
                           "align_aperture": self.align_aperture,
                           "abort_md3": self.abort_md3,
                           "empty_mount": self.empty_mount,
                           "restart_mxcube": self.restart_mxcube,
                           "anneal": self.anneal,
                           "focus_beam_20": self.focus_beam_20,
                           "focus_beam_50": self.focus_beam_50,
                           "focus_beam_100": self.focus_beam_100,
                           "check_laser_shutter": self.check_laser_shutter,
                           "start_beamtime": self.start_beamtime }
        self.command_list = eval(self.get_property("command_list"))

    def get_commands(self):
        commands = []
        for command in self.command_list:
            commands.append(self.dispatcher[command])
        return commands
    
    def get_annotated_commands(self):
        return []
