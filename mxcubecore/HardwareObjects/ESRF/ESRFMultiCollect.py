from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractMultiCollect import *
import logging
import time
import os
import math
from HardwareRepository.HardwareObjects.queue_model_objects import PathTemplate
from HardwareRepository.ConvertUtils import string_types
from HardwareRepository import HardwareRepository as HWR

from ESRF.ESRFMetadataManagerClient import MXCuBEMetadataClient


try:
    from httplib import HTTPConnection
except:
    # Python3
    from http.client import HTTPConnection

try:
    from urllib import urlencode
except:
    # Python3
    from urllib.parse import urlencode


# class FixedEnergy:
#     def __init__(self, wavelength, energy):
#         self.wavelength = wavelength
#         self.energy = energy

#     def set_wavelength(self, wavelength):
#         return

#     def set_energy(self, energy):
#         return

#     def get_energy(self):
#         return self.energy

#     def get_wavelength(self):
#         return self.wavelength


# class TunableEnergy:
#     @task
#     def set_wavelength(self, wavelength):
#         if HWR.beamline.tunable_wavelength:
#             return HWR.beamline.energy.set_wavelength(wavelength)
#         else:
#             return

#     @task
#     def set_energy(self, energy):
#          if HWR.beamline.tunable_wavelength:
#              return HWR.beamline.energy.set_value(energy)
#          else:
#              return

#     def get_energy(self):
#         return HWR.beamline.energy.get_value()

#     def get_wavelength(self):
#         return HWR.beamline.energy.get_wavelength()


# class CcdDetector:
#     def __init__(self, detector_class=None):
#         self._detector = detector_class() if detector_class else None

#     def init(self, config, collect_obj):
#         self.collect_obj = collect_obj
#         if self._detector:
#             self._detector.add_channel = self.add_channel
#             self._detector.add_command = self.add_command
#             self._detector.get_channel_object = self.get_channel_object
#             self._detector.get_command_object = self.get_command_object
#             self._detector.init(config, collect_obj)

#     @task
#     def prepare_acquisition(
#         self,
#         take_dark,
#         start,
#         osc_range,
#         exptime,
#         npass,
#         number_of_images,
#         comment="",
#         energy=None,
#     ):
#         if osc_range < 1e-4:
#             trigger_mode = "INTERNAL_TRIGGER"
#         else:
#             trigger_mode = "EXTERNAL_TRIGGER"

#         if self._detector:
#             self._detector.prepare_acquisition(
#                 take_dark,
#                 start,
#                 osc_range,
#                 exptime,
#                 npass,
#                 number_of_images,
#                 comment,
#                 energy,
#                 trigger_mode,
#             )
#         else:
#             self.get_channel_object("take_dark").setValue(take_dark)
#             self.execute_command(
#                 "prepare_acquisition",
#                 take_dark,
#                 start,
#                 osc_range,
#                 exptime,
#                 npass,
#                 comment,
#                 energy,
#                 trigger_mode,
#             )

#     @task
#     def set_detector_filenames(
#         self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
#     ):
#         if self._detector:
#             self._detector.set_detector_filenames(
#                 frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
#             )
#         else:
#             self.get_command_object("prepare_acquisition").executeCommand(
#                 'setMxCollectPars("current_phi", %f)' % start
#             )
#             self.get_command_object("prepare_acquisition").executeCommand(
#                 'setMxCurrentFilename("%s")' % filename
#             )
#             self.get_command_object("prepare_acquisition").executeCommand(
#                 "ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True
#             )

#     @task
#     def prepare_oscillation(self, start, osc_range, exptime, npass):
#         if osc_range < 1e-4:
#             # still image
#             pass
#         else:
#             self.collect_obj.do_prepare_oscillation(
#                 start, start + osc_range, exptime, npass
#             )
#         return (start, start + osc_range)

#     @task
#     def start_acquisition(self, exptime, npass, first_frame):
#         if self._detector:
#             self._detector.start_acquisition(exptime, npass, first_frame)
#         else:
#             self.execute_command("start_acquisition")

#     @task
#     def no_oscillation(self, exptime):
#         self.collect_obj.open_fast_shutter()
#         time.sleep(exptime)
#         self.collect_obj.close_fast_shutter()

#     @task
#     def do_oscillation(self, start, end, exptime, npass):
#         still = math.fabs(end - start) < 1e-4
#         if still:
#             self.no_oscillation(exptime)
#         else:
#             self.collect_obj.oscil(start, end, exptime, npass)

#     @task
#     def write_image(self, last_frame):
#         if self._detector:
#             self._detector.write_image(last_frame)
#         else:
#             if last_frame:
#                 self.execute_command("flush_detector")
#             else:
#                 self.execute_command("write_image")

#     def stop_acquisition(self):
#         # detector readout
#         if self._detector:
#             self._detector.stop_acquisition()
#         else:
#             self.execute_command("detector_readout")

#     @task
#     def reset_detector(self):
#         if self._detector:
#             self._detector.stop()
#         else:
#             self.get_command_object("reset_detector").abort()
#             self.execute_command("reset_detector")


# class PixelDetector:
#     def __init__(self, detector_class=None):
#         self._detector = detector_class() if detector_class else None
#         self.shutterless = True
#         self.new_acquisition = True
#         self.oscillation_task = None
#         self.shutterless_exptime = None
#         self.shutterless_range = None
#         self._mesh_steps = None

#     def init(self, config, collect_obj):
#         self.collect_obj = collect_obj
#         if self._detector:
#             self._detector.add_channel = self.add_channel
#             self._detector.add_command = self.add_command
#             self._detector.get_channel_object = self.get_channel_object
#             self._detector.get_command_object = self.get_command_object
#             self._detector.init(config, collect_obj)

#     def last_image_saved(self):
#         return self._detector.last_image_saved()

#     def get_deadtime(self):
#         return self._detector.get_deadtime()

#     @task
#     def prepare_acquisition(
#         self,
#         take_dark,
#         start,
#         osc_range,
#         exptime,
#         npass,
#         number_of_images,
#         comment="",
#         energy=None,
#         trigger_mode=None,
#     ):
#         take_dark = 0
#         self.new_acquisition = True
#         if trigger_mode is None:
#             if osc_range < 1e-4:
#                 trigger_mode = "INTERNAL_TRIGGER"
#             else:
#                 trigger_mode = "EXTERNAL_TRIGGER"
#             if self._mesh_steps > 1:
#                 trigger_mode = "EXTERNAL_prepare_acquisition_MULTI"
#                 # reset mesh steps
#                 self._mesh_steps = 1

#         if self.shutterless:
#             self.shutterless_range = osc_range * number_of_images
#             self.shutterless_exptime = (
#                 exptime + self._detector.get_deadtime()
#             ) * number_of_images
#         if self._detector:
#             self._detector.prepare_acquisition(
#                 take_dark,
#                 start,
#                 osc_range,
#                 exptime,
#                 npass,
#                 number_of_images,
#                 comment,
#                 energy,
#                 trigger_mode,
#             )
#         else:
#             self.execute_command(
#                 "prepare_acquisition",
#                 take_dark,
#                 start,
#                 osc_range,
#                 exptime,
#                 npass,
#                 comment,
#                 energy,
#                 trigger_mode,
#             )

#     @task
#     def set_detector_filenames(
#         self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
#     ):
#         if self.shutterless and not self.new_acquisition:
#             return

#         if self._detector:
#             self._detector.set_detector_filenames(
#                 frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
#             )
#         else:
#             self.get_command_object("prepare_acquisition").executeCommand(
#                 'setMxCollectPars("current_phi", %f)' % start
#             )
#             self.get_command_object("prepare_acquisition").executeCommand(
#                 'setMxCurrentFilename("%s")' % filename
#             )
#             self.get_command_object("prepare_acquisition").executeCommand(
#                 "ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True
#             )

#     @task
#     def prepare_oscillation(self, start, osc_range, exptime, npass):
#         if self.shutterless:
#             end = start + self.shutterless_range
#             if self.new_acquisition:
#                 self.collect_obj.do_prepare_oscillation(
#                     start, end, self.shutterless_exptime, npass
#                 )
#             return (start, end)
#         else:
#             if osc_range < 1e-4:
#                 # still image
#                 pass
#             else:
#                 self.collect_obj.do_prepare_oscillation(
#                     start, start + osc_range, exptime, npass
#                 )
#             return (start, start + osc_range)

#     @task
#     def start_acquisition(self, exptime, npass, first_frame):
#         try:
#             self.collect_obj.getObjectByRole("detector_cover").set_out()
#         except Exception:
#             pass

#         if not first_frame and self.shutterless:
#             pass
#         else:
#             if self._detector:
#                 self._detector.start_acquisition()
#             else:
#                 self.execute_command("start_acquisition")

#     @task
#     def no_oscillation(self, exptime):
#         self.collect_obj.open_fast_shutter()
#         time.sleep(exptime)
#         self.collect_obj.close_fast_shutter()

#     @task
#     def do_oscillation(self, start, end, exptime, npass):
#         still = math.fabs(end - start) < 1e-4
#         if self.shutterless:
#             if self.new_acquisition:
#                 # only do this once per collect
#                 # make oscillation an asynchronous task => do not wait here
#                 if still:
#                     self.oscillation_task = self.no_oscillation(
#                         self.shutterless_exptime, wait=False
#                     )
#                 else:
#                     self.oscillation_task = self.collect_obj.oscil(
#                         start, end, self.shutterless_exptime, 1, wait=False
#                     )
#             if self.oscillation_task.ready():
#                 self.oscillation_task.get()
#         else:
#             if still:
#                 self.no_oscillation(exptime)
#             else:
#                 self.collect_obj.oscil(start, end, exptime, npass)

#     @task
#     def write_image(self, last_frame):
#         if last_frame:
#             if self.shutterless:
#                 self.oscillation_task.get()

#     def stop_acquisition(self):
#         self.new_acquisition = False

#     @task
#     def reset_detector(self):
#         if self.shutterless:
#             self.oscillation_task.kill()
#         if self._detector:
#             self._detector.stop()
#         else:
#             self.get_command_object("reset_detector").abort()
#             self.execute_command("reset_detector")


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

        self.setControlObjects(
            diffractometer=self.getObjectByRole("diffractometer"),
            sample_changer=self.getObjectByRole("sample_changer"),
            lims=self.getObjectByRole("dbserver"),
            safety_shutter=self.getObjectByRole("safety_shutter"),
            machine_current=self.getObjectByRole("machine_current"),
            cryo_stream=self.getObjectByRole("cryo_stream"),
            energy=self.getObjectByRole("energy"),
            resolution=self.getObjectByRole("resolution"),
            detector_distance=self.getObjectByRole("detector_distance"),
            transmission=self.getObjectByRole("transmission"),
            undulators=self.getObjectByRole("undulators"),
            flux=self.getObjectByRole("flux"),
            detector=self.getObjectByRole("detector"),
            beam_info=self.getObjectByRole("beam_info"),
        )

        try:
            undulators = self["undulator"]
        except KeyError:
            undulators = []

        beam_div_hor, beam_div_ver = HWR.beamline.beam.get_beam_divergence()

        self.setBeamlineConfiguration(
            synchrotron_name="ESRF",
            directory_prefix=self.getProperty("directory_prefix"),
            default_exposure_time=HWR.beamline.detector.getProperty(
                "default_exposure_time"
            ),
            minimum_exposure_time=HWR.beamline.detector.getProperty(
                "minimum_exposure_time"
            ),
            detector_fileext=HWR.beamline.detector.getProperty("file_suffix"),
            detector_type=HWR.beamline.detector.getProperty("type"),
            detector_manufacturer=HWR.beamline.detector.getProperty("manufacturer"),
            detector_model=HWR.beamline.detector.getProperty("model"),
            detector_binning_mode=HWR.beamline.detector.getProperty("binning_mode"),
            detector_px=HWR.beamline.detector.getProperty("px"),
            detector_py=HWR.beamline.detector.getProperty("py"),
            undulators=undulators,
            focusing_optic=self.getProperty("focusing_optic"),
            monochromator_type=self.getProperty("monochromator"),
            beam_divergence_vertical=beam_div_ver,
            beam_divergence_horizontal=beam_div_hor,
            polarisation=self.getProperty("polarisation"),
            maximum_phi_speed=self.getProperty("maximum_phi_speed"),
            minimum_phi_oscillation=self.getProperty("minimum_phi_oscillation"),
            input_files_server=self.getProperty("input_files_server"),
        )

        # self._detector.init(HWR.beamline.detector, self)

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    @task
    def take_crystal_snapshots(self, number_of_snapshots):
        HWR.beamline.diffractometer.take_snapshots(number_of_snapshots, wait=True)

    @task
    def data_collection_hook(self, data_collect_parameters):
        if self._metadataClient is None:
            self._metadataClient = MXCuBEMetadataClient(self)
        self._metadataClient.start(data_collect_parameters)

    @task
    def data_collection_end_hook(self, data_collect_parameters):
        self._detector._emit_status()
        self._metadataClient.end(data_collect_parameters)

    def prepare_oscillation(
        self,
        start,
        osc_range,
        exptime,
        number_of_images,
        shutterless,
        npass,
        first_frame,
    ):
        if shutterless:
            end = start + osc_range * number_of_images
            exptime = (exptime + self._detector.get_deadtime()) * number_of_images

            if first_frame:
                self.do_prepare_oscillation(start, end, exptime, npass)
        else:
            if osc_range < 1e-4:
                # still image
                end = start
            else:
                end = start + osc_range
                self.do_prepare_oscillation(start, end, exptime, npass)

        return start, end

    @task
    def no_oscillation(self, exptime):
        self.open_fast_shutter()
        time.sleep(exptime)
        self.close_fast_shutter()

    @task
    def do_oscillation(
        self, start, end, exptime, number_of_images, shutterless, npass, first_frame
    ):
        still = math.fabs(end - start) < 1e-4

        if shutterless:
            if first_frame:
                exptime = (exptime + self._detector.get_deadtime()) * number_of_images
                # only do this once per collect
                # make oscillation an asynchronous task => do not wait here
                if still:
                    self.oscillation_task = self.no_oscillation(exptime, wait=False)
                else:
                    self.oscillation_task = self.oscil(
                        start, end, exptime, 1, wait=False
                    )

            if self.oscillation_task.ready():
                self.oscillation_task.get()
        else:
            if still:
                self.no_oscillation(exptime)
            else:
                self.oscil(start, end, exptime, npass)

    @task
    def oscil(self, start, end, exptime, npass, wait=False):
        if math.fabs(end - start) < 1e-4:
            self.open_fast_shutter()
            time.sleep(exptime)
            self.close_fast_shutter()
        else:
            return self.execute_command("do_oscillation", start, end, exptime, npass)

    def set_wavelength(self, wavelength):
        if HWR.beamline.tunable_wavelength:
            return HWR.beamline.energy.set_wavelength(wavelength)
        else:
            return

    def set_energy(self, energy):
        if HWR.beamline.tunable_wavelength:
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
        HWR.beamline.diffractometer.set_phase("Centring", wait=True, timeout=200)

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
                motor = HWR.beamline.diffractometer.getDeviceByRole(motor_role)
                del motor_positions_copy[motor_role]
                if motor is None:
                    continue
                motor_positions_copy[motor] = position

            logging.getLogger("HWR").info(
                "Moving motor '%s' to %f", motor.getMotorMnemonic(), position
            )
            motor.set_value(position)

        while any([motor.motorIsMoving() for motor in motor_positions_copy]):
            logging.getLogger("HWR").info("Waiting for end of motors motion")
            time.sleep(0.02)

    def open_safety_shutter(self):
        try:
            HWR.beamline.safety_shutter.set_value(
                HWR.beamline.safety_shutter.VALUES.OPEN, timeout=10
            )
        except Exception:
            logging.getLogger("HWR").exception("")

    def safety_shutter_opened(self):
        state = False

        try:
            state = HWR.beamline.safety_shutter.get_state().name == "OPENED"
        except Exception:
            logging.getLogger("HWR").exception("")
            state = True

        return state

    @task
    def close_safety_shutter(self):
        try:
            HWR.beamline.safety_shutter.set_value(
                HWR.beamline.safety_shutter.VALUES["CLOSED"]
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
            self.mesh_num_lines
        )

    def set_detector_filenames(self, is_first_frame, frame_number, start, filename, shutterless):
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

    def last_image_saved(self):
        return self._detector.last_image_saved()

    def stop_acquisition(self):
        return self._detector.stop_acquisition()

    def reset_detector(self):
        return self._detector.reset()

    def prepare_input_files(
        self, files_directory, prefix, run_number, process_directory
    ):
        i = 1

        while True:
            xds_input_file_dirname = "xds_%s_run%s_%d" % (prefix, run_number, i)
            autoprocessing_input_file_dirname = "autoprocessing_%s_run%s_%d" % (
                prefix,
                run_number,
                i,
            )
            autoprocessing_directory = os.path.join(
                process_directory, autoprocessing_input_file_dirname
            )

            if not os.path.exists(autoprocessing_directory):
                break

            i += 1

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (prefix, run_number, i)

        hkl2000_dirname = "hkl2000_%s_run%s_%d" % (prefix, run_number, i)

        self.raw_data_input_file_dir = os.path.join(
            files_directory, "process", xds_input_file_dirname
        )
        self.mosflm_raw_data_input_file_dir = os.path.join(
            files_directory, "process", mosflm_input_file_dirname
        )
        self.raw_hkl2000_dir = os.path.join(files_directory, "process", hkl2000_dirname)

        for dir in (
            self.raw_data_input_file_dir,
            self.mosflm_raw_data_input_file_dir,
            self.raw_hkl2000_dir,
            autoprocessing_directory,
        ):
            self.create_directories(dir)
            logging.info("Creating processing input file directory: %s", dir)
            os.chmod(dir, 0o777)

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
            _gaps = HWR.beamline.undulators
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
                return HWR.beamline.machine_info.getCurrent()
            except Exception:
                return -1
        else:
            return 0

    def get_machine_message(self):
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.getMessage()
        else:
            return ""

    def get_machine_fill_mode(self):
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.getFillMode()
        else:
            ""

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

    def isConnected(self):
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
        host, port = self.getProperty("bes_jpeg_hostport").split(":")
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
        self.get_channel_object("helical").setValue(1 if helical_on else 0)

    def set_helical_pos(self, helical_oscil_pos):
        self.get_channel_object("helical_pos").setValue(helical_oscil_pos)

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
