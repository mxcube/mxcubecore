import logging
import math
import os
import time
from http.client import HTTPConnection
from urllib.parse import urlencode

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractMultiCollect import *
from mxcubecore.model.queue_model_objects import PathTemplate
from mxcubecore.utils.conversion import string_types


class ESRFMultiCollect(AbstractMultiCollect, HardwareObject):
    def __init__(self, name):
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._centring_status = None
        self._metadataClient = None
        self.__mesh_steps = None
        self._mesh_range = None

    @property
    def _mesh_steps(self):
        return self.__mesh_steps

    @_mesh_steps.setter
    def _mesh_steps(self, steps):
        self.__mesh_steps = steps
        self._detector._mesh_steps = steps

    def execute_command(self, command_name, *args, **kwargs):
        wait = kwargs.get("wait", True)
        cmd_obj = self.get_command_object(command_name)
        return cmd_obj(*args, wait=wait)

    def init(self):
        self._detector = HWR.beamline.detector
        self.number_of_snapshots = self.get_property("num_snapshots", 4)

        self.setControlObjects(
            diffractometer=self.get_object_by_role("diffractometer"),
            sample_changer=self.get_object_by_role("sample_changer"),
            lims=self.get_object_by_role("dbserver"),
            safety_shutter=self.get_object_by_role("safety_shutter"),
            machine_current=self.get_object_by_role("machine_current"),
            cryo_stream=self.get_object_by_role("cryo_stream"),
            energy=self.get_object_by_role("energy"),
            resolution=self.get_object_by_role("resolution"),
            detector_distance=self.get_object_by_role("detector_distance"),
            transmission=self.get_object_by_role("transmission"),
            undulators=self.get_object_by_role("undulators"),
            flux=self.get_object_by_role("flux"),
            detector=self.get_object_by_role("detector"),
            beam_info=self.get_object_by_role("beam_info"),
        )

        try:
            undulators = self["undulator"]
        except KeyError:
            undulators = []

        beam_div_hor, beam_div_ver = HWR.beamline.beam.get_beam_divergence()

        self.setBeamlineConfiguration(
            synchrotron_name="ESRF",
            directory_prefix=self.get_property("directory_prefix"),
            default_exposure_time=HWR.beamline.detector.get_property(
                "default_exposure_time"
            ),
            minimum_exposure_time=HWR.beamline.detector.get_property(
                "minimum_exposure_time"
            ),
            detector_fileext=HWR.beamline.detector.get_property("file_suffix"),
            detector_type=HWR.beamline.detector.get_property("type"),
            detector_manufacturer=HWR.beamline.detector.get_property("manufacturer"),
            detector_model=HWR.beamline.detector.get_property("model"),
            detector_binning_mode=HWR.beamline.detector.get_property("binning_mode"),
            detector_px=HWR.beamline.detector.get_property("px"),
            detector_py=HWR.beamline.detector.get_property("py"),
            undulators=undulators,
            focusing_optic=self.get_property("focusing_optic"),
            monochromator_type=self.get_property("monochromator"),
            beam_divergence_vertical=beam_div_ver,
            beam_divergence_horizontal=beam_div_hor,
            polarisation=self.get_property("polarisation"),
            maximum_phi_speed=self.get_property("maximum_phi_speed"),
            minimum_phi_oscillation=self.get_property("minimum_phi_oscillation"),
            input_files_server=self.get_property("input_files_server"),
        )

        # self._detector.init(HWR.beamline.detector, self)

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    @task
    def data_collection_end_hook(self, data_collect_parameters):
        self._detector._emit_status()

    def prepare_oscillation(
        self,
        start,
        osc_range,
        exptime,
        number_of_images,
        shutterless,
        first_frame,
    ):
        if shutterless:
            end = start + osc_range * number_of_images
            exptime = (exptime + self._detector.get_deadtime()) * number_of_images

            if first_frame:
                self.do_prepare_oscillation(start, end, exptime)
        else:
            if osc_range < 1e-4:
                # still image
                end = start
            else:
                end = start + osc_range
                self.do_prepare_oscillation(start, end, exptime)

        return start, end

    @task
    def no_oscillation(self, exptime):
        self.open_fast_shutter()
        time.sleep(exptime)
        self.close_fast_shutter()


    @task
    def do_oscillation(
        self, start, end, exptime, number_of_images, shutterless, first_frame,
    ):
        if shutterless:
            if first_frame:
                exptime = (exptime + self._detector.get_deadtime()) * number_of_images
                self.oscillation_task = self.oscil(
                    start, end, exptime, number_of_images, wait=False
                )

            if self.oscillation_task.ready():
                self.oscillation_task.get()
        else:
            self.oscil(start, end, exptime, number_of_images)

    @task
    def oscil(self, start, end, exptime, number_of_images, wait=False):
        if math.fabs(end - start) < 1e-4:
            self.open_fast_shutter()
            time.sleep(exptime)
            self.close_fast_shutter()
        else:
            return self.execute_command("do_oscillation", start, end, exptime, number_of_images)

    def set_wavelength(self, wavelength):
        if HWR.beamline.config.tunable_wavelength:
            return HWR.beamline.energy.set_wavelength(wavelength)
        else:
            return

    def set_energy(self, energy):
        if HWR.beamline.config.tunable_wavelength:
            return HWR.beamline.energy.set_value(energy)
        else:
            return

    def data_collection_cleanup(self):
        try:
            self.close_fast_shutter()
            self.stop_oscillation()
            HWR.beamline.detector.stop_acquisition()
        except Exception:
            logging.getLogger("HWR").exception("")

    def queue_finished_cleanup(self):
        logging.getLogger("user_level_log").info("Queue execution finished")

    @task
    def close_fast_shutter(self):
        self.execute_command("close_fast_shutter")

    @task
    def open_fast_shutter(self):
        self.execute_command("open_fast_shutter")

    @task
    def move_motors(self, motor_position_dict):
        # We do not wnta to modify the input dict
        motor_positions_copy = motor_position_dict.copy()
        for motor in motor_positions_copy.keys():  # iteritems():
            position = motor_positions_copy[motor]
            if isinstance(motor, string_types):
                # find right motor object from motor role in diffractometer obj.
                motor_role = motor
                motor = HWR.beamline.diffractometer.get_deviceby_role(motor_role)
                del motor_positions_copy[motor_role]
                if motor is None:
                    continue
                motor_positions_copy[motor] = position

            logging.getLogger("HWR").info(
                "Moving motor '%s' to %f", motor.get_motor_mnemonic(), position
            )
            motor.set_value(position)

        while any([motor.motorIsMoving() for motor in motor_positions_copy]):
            logging.getLogger("HWR").info("Waiting for end of motors motion")
            time.sleep(0.02)

    def open_safety_shutter(self):
        if HWR.beamline.safety_shutter.get_value().name == "CLOSED":
            try:
                logging.getLogger("user_level_log").info("Opening safety shutter")
                HWR.beamline.safety_shutter.set_value(
                    HWR.beamline.safety_shutter.VALUES.OPEN, timeout=10
                )
            except Exception:
                logging.getLogger("HWR").exception("")

    def safety_shutter_opened(self):
        state = False

        try:
            state = HWR.beamline.safety_shutter.get_value().name == "OPEN"
        except Exception:
            logging.getLogger("HWR").exception("")
            state = True

        return state

    @task
    def close_safety_shutter(self):
        if HWR.beamline.safety_shutter.get_value().name == "OPEN":
            try:
                HWR.beamline.safety_shutter.set_value(
                    HWR.beamline.safety_shutter.VALUES.CLOSED
                )
            except Exception:
                logging.getLogger("HWR").exception("")

    @task
    def prepare_intensity_monitors(self):
        try:
            self.execute_command("adjust_gains")
        except AttributeError:
            pass

    def prepare_acquisition(
        self,
        take_dark,
        start,
        osc_range,
        exptime,
        npass,
        number_of_images,
        comment="",
    ):
        self._detector.prepare_acquisition(
            take_dark,
            start,
            osc_range,
            exptime,
            npass,
            number_of_images,
            comment,
            self.mesh,
            self.mesh_num_lines,
        )

    def set_detector_filenames(
        self, is_first_frame, frame_number, start, filename, shutterless
    ):
        if is_first_frame or not shutterless:
            return self._detector.set_detector_filenames(frame_number, start, filename)

    def stop_oscillation(self):
        HWR.beamline.diffractometer.abort_cmd()

    def start_acquisition(self, exptime, npass, first_frame, shutterless):
        if first_frame:
            return self._detector.start_acquisition()

    @task
    def write_image(self, last_frame):
        if last_frame:
            res = self._detector.wait_ready()
            self._detector._emit_status()
            return res

    def last_image_saved(self, total_time, exptime, num_images):
        # check here if fast shutter is open ?
        if HWR.beamline.detector.status["acq_satus"] == "RUNNING":
            return int(total_time / exptime)
        else:
            return HWR.beamline.detector.last_image_saved()

    def stop_acquisition(self):
        return self._detector.stop_acquisition()

    def reset_detector(self):
        return self._detector.reset()

    def prepare_input_files(
        self, files_directory, prefix, run_number, process_directory
    ):

        autoprocessing_input_file_dirname = "autoprocessing"
        autoprocessing_directory = os.path.join(
            process_directory, autoprocessing_input_file_dirname
        )
        xds_input_file_dirname = "xds_%s_run%s" % (prefix, run_number,)
        mosflm_input_file_dirname = "mosflm_%s_run%s" % (prefix, run_number)
        hkl2000_dirname = "hkl2000_%s_run%s" % (prefix, run_number)

        i = 1
        while os.path.exists(autoprocessing_directory):
            autoprocessing_input_file_dirname = "autoprocessing_%d" % i
            autoprocessing_directory = os.path.join(
                process_directory, autoprocessing_input_file_dirname
            )
            xds_input_file_dirname = "xds_%s_run%s_%d" % (prefix, run_number, i)
            mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (prefix, run_number, i)
            hkl2000_dirname = "hkl2000_%s_run%s_%d" % (prefix, run_number, i)
            i += 1

        self.raw_data_input_file_dir = os.path.join(
            files_directory, "process", xds_input_file_dirname
        )
        self.mosflm_raw_data_input_file_dir = os.path.join(
            files_directory, "process", mosflm_input_file_dirname
        )
        self.raw_hkl2000_dir = os.path.join(files_directory, "process", hkl2000_dirname)

        for dir0 in (
            self.raw_data_input_file_dir,
            self.mosflm_raw_data_input_file_dir,
            self.raw_hkl2000_dir,
            autoprocessing_directory,
        ):
            self.create_directories(dir0)
            logging.info("Creating processing input file directory: %s", dir0)
            os.chmod(dir0, 0o777)

        try:
            try:
                os.symlink(files_directory, os.path.join(process_directory, "links"))
            except os.error as e:
                if e.errno != errno.EEXIST:
                    raise
        except Exception:
            logging.exception("Could not create processing file directory")

        return autoprocessing_directory, "", ""

    @task
    def write_input_files(self, collection_id):
        # assumes self.xds_directory and self.mosflm_directory are valid
        conn = HTTPConnection(self.bl_config.input_files_server)

        # hkl input files
        input_file_dir = self.raw_hkl2000_dir
        file_prefix = "../.."
        hkl_file_path = os.path.join(input_file_dir, "def.site")

        conn.request("GET", "/def.site/%d?basedir=%s" % (collection_id, file_prefix))
        hkl_file = open(hkl_file_path, "w")
        r = conn.getresponse()

        if r.status != 200:
            logging.error("Could not create hkl input file")
        else:
            hkl_file.write(r.read().decode())
        hkl_file.close()
        os.chmod(hkl_file_path, 0o666)

        for input_file_dir, file_prefix in (
            (self.raw_data_input_file_dir, "../.."),
            (self.xds_directory, "../links"),
        ):
            xds_input_file = os.path.join(input_file_dir, "XDS.INP")
            conn.request("GET", "/xds.inp/%d?basedir=%s" % (collection_id, file_prefix))
            xds_file = open(xds_input_file, "w")
            res = conn.getresponse()
            if res.status != 200:
                logging.error("Could not create xds input file")
            else:
                xds_file.write(res.read().decode())
            xds_file.close()
            os.chmod(xds_input_file, 0o666)

        input_file_dir = self.mosflm_raw_data_input_file_dir
        file_prefix = "../.."
        mosflm_input_file = os.path.join(input_file_dir, "mosflm.inp")
        conn.request("GET", "/mosflm.inp/%d?basedir=%s" % (collection_id, file_prefix))
        mosflm_file = open(mosflm_input_file, "w")
        mosflm_file.write(conn.getresponse().read().decode())
        mosflm_file.close()
        os.chmod(mosflm_input_file, 0o666)

        # also write input file for STAC
        for stac_om_input_file_name, stac_om_dir in (
            ("xds.descr", self.xds_directory),
            ("mosflm.descr", self.mosflm_raw_data_input_file_dir),
            ("xds.descr", self.raw_data_input_file_dir),
        ):
            stac_om_input_file = os.path.join(stac_om_dir, stac_om_input_file_name)
            conn.request("GET", "/stac.descr/%d" % collection_id)
            stac_om_file = open(stac_om_input_file, "w")
            stac_template = conn.getresponse().read().decode()
            if stac_om_input_file_name.startswith("xds"):
                om_type = "xds"
                if stac_om_dir == self.raw_data_input_file_dir:
                    om_filename = os.path.join(stac_om_dir, "CORRECT.LP")
                else:
                    om_filename = os.path.join(
                        stac_om_dir, "xds_fastproc", "CORRECT.LP"
                    )
            else:
                om_type = "mosflm"
                om_filename = os.path.join(stac_om_dir, "bestfile.par")

            stac_om_file.write(
                stac_template.format(
                    omfilename=om_filename,
                    omtype=om_type,
                    phi=HWR.beamline.diffractometer.phiMotor.get_value(),
                    sampx=HWR.beamline.diffractometer.sampleXMotor.get_value(),
                    sampy=HWR.beamline.diffractometer.sampleYMotor.get_value(),
                    phiy=HWR.beamline.diffractometer.phiyMotor.get_value(),
                )
            )
            stac_om_file.close()
            os.chmod(stac_om_input_file, 0o666)

    def get_wavelength(self):
        return HWR.beamline.energy.get_wavelength()

    def get_undulators_gaps(self):
        all_gaps = {"Unknown": None}
        _gaps = {}

        try:
            _gaps = HWR.beamline.config.undulators
        except Exception:
            logging.getLogger("HWR").exception("Could not get undulator gaps")
        all_gaps.clear()
        for key in _gaps:
            if "_Position" in key:
                nkey = key[:-9]
                all_gaps[nkey] = _gaps[key]
            else:
                all_gaps = _gaps
        return all_gaps

    def get_resolution_at_corner(self):
        return self.execute_command("get_resolution_at_corner")

    def get_beam_size(self):
        return (
            self.execute_command("get_beam_size_x"),
            self.execute_command("get_beam_size_y"),
        )

    def get_slit_gaps(self):
        return (
            self.execute_command("get_slit_gap_h"),
            self.execute_command("get_slit_gap_v"),
        )

    def get_beam_shape(self):
        return self.execute_command("get_beam_shape")

    # def get_measured_intensity(self):
    #     try:
    #         val = self.get_channel_object("image_intensity").getValue()
    #         return float(val)
    #     except Exception:
    #         return 0

    def get_machine_current(self):
        if HWR.beamline.machine_info:
            try:
                return HWR.beamline.machine_info.get_current()
            except Exception:
                return -1
        else:
            return 0

    def get_machine_message(self):
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.get_message()
        else:
            return ""

    def get_machine_fill_mode(self):
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.get_fill_mode()
        else:
            """"""

    def get_cryo_temperature(self):
        while True:
            logging.info("Reading cryostream temperature")
            try:
                T = HWR.beamline.cryo_stream.getTemperature()
            except Exception:
                time.sleep(0.1)
                continue
            else:
                return T

    def get_current_energy(self):
        return HWR.beamline.energy.get_value()

    def get_beam_centre(self):
        return (
            self.execute_command("get_beam_centre_x"),
            self.execute_command("get_beam_centre_y"),
        )

    def getBeamlineConfiguration(self, *args):
        # TODO: change this to stop using a dictionary at the other end
        return self.bl_config._asdict()

    def is_connected(self):
        return True

    def is_ready(self):
        return True

    def sampleChangerHO(self):
        return HWR.beamline.sample_changer

    def diffractometer(self):
        return HWR.beamline.diffractometer

    def dbServerHO(self):
        return HWR.beamline.lims

    def sanityCheck(self, collect_params):
        return

    def setBrick(self, brick):
        return

    def directoryPrefix(self):
        return self.bl_config.directory_prefix

    def store_image_in_lims(self, frame, first_frame, last_frame):
        if first_frame or last_frame:
            return True

    @task
    def generate_image_jpeg(self, filename, jpeg_path, jpeg_thumbnail_path):
        directories = filename.split(os.path.sep)
        try:
            if directories[1] == "data" and directories[2] == "gz":
                if directories[3] == "visitor":
                    proposal = directories[4]
                    beamline = directories[5]
                elif directories[4] == "inhouse":
                    proposal = directories[5]
                    beamline = directories[3]
                else:
                    proposal = "unknown"
                    beamline = "unknown"

            elif directories[2] == "visitor":
                beamline = directories[4]
                proposal = directories[3]
            else:
                beamline = directories[2]
                proposal = directories[4]
        except Exception:
            beamline = "unknown"
            proposal = "unknown"
        host, port = self.get_property("bes_jpeg_hostport").split(":")
        conn = HTTPConnection(host, int(port))

        params = urlencode(
            {
                "image_path": filename,
                "jpeg_path": jpeg_path,
                "jpeg_thumbnail_path": jpeg_thumbnail_path,
                "initiator": beamline,
                "externalRef": proposal,
                "reuseCase": "true",
            }
        )
        conn.request(
            "POST",
            "/BES/bridge/rest/processes/CreateThumbnails/RUN?%s" % params,
            headers={"Accept": "text/plain"},
        )
        conn.getresponse()

    """
    getOscillation
        Description: Returns the parameters (and results) of an oscillation.
        Type       : method
        Arguments  : oscillation_id (int; the oscillation id, the last parameters of the collectOscillationStarted
                                     signal)
        Returns    : tuple; (blsampleid,barcode,location,parameters)
    """

    def getOscillation(self, oscillation_id):
        return self.oscillations_history[oscillation_id - 1]

    def sampleAcceptCentring(self, accepted, centring_status):
        self.sample_centring_done(accepted, centring_status)

    def setCentringStatus(self, centring_status):
        self._centring_status = centring_status

    """
    getOscillations
        Description: Returns the history of oscillations for a session
        Type       : method
        Arguments  : session_id (int; the session id, stored in the "sessionId" key in each element
                                 of the parameters list in the collect method)
        Returns    : list; list of all oscillation_id for the specified session
    """

    def getOscillations(self, session_id):
        # TODO
        return []

    def set_helical(self, helical_on):
        self.get_channel_object("helical").set_value(1 if helical_on else 0)

    def set_helical_pos(self, helical_oscil_pos):
        self.get_channel_object("helical_pos").set_value(helical_oscil_pos)

    def get_archive_directory(self, directory):
        pt = PathTemplate()
        pt.directory = directory
        return pt.get_archive_directory()

    def setMeshScanParameters(self, mesh_steps, mesh_range):
        """
        Descript. :
        """
        self._mesh_steps = mesh_steps
        self._mesh_range = mesh_range
