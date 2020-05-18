"""
 File:  PX1Collect.py

"""

import os
import sys
import time
import logging
import gevent
import subprocess
import socket

from HardwareRepository.Command.Tango import DeviceProxy

from HardwareRepository.TaskUtils import task
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractCollect import AbstractCollect

from SOLEILMergeImage import merge as merge_images

from HardwareRepository import HardwareRepository as HWR

__author__ = "Vicente Rey Bakaikoa"
__credits__ = ["MXCuBE collaboration"]
__version__ = "2.3"


class PX1Collect(AbstractCollect, HardwareObject):
    """Main data collection class. Inherited from AbstractMulticollect
       Collection is done by setting collection parameters and
       executing collect command
    """

    adxv_host = "127.0.0.1"
    adxv_port = 8100
    adxv_interval = 2.0  # minimum time (in seconds) between image refresh on adxv

    goimg_dir = "/nfs/ruche/share-temp/Proxima/.goimgpx1"
    goimg_filename = "goimg.db"

    characterization_nb_merged_images = 10

    def __init__(self, name):
        """

        :param name: name of the object
        :type name: string
        """

        AbstractCollect.__init__(self)
        HardwareObject.__init__(self, name)

        self._error_msg = ""
        self.owner = None
        self.osc_id = None
        self._collecting = None

        self.mxlocal = None

        self.helical_positions = None

    def init(self):
        """
        Init method
        """

        self.collect_devname = self.getProperty("tangoname")
        self.collect_device = DeviceProxy(self.collect_devname)

        self.collect_state_chan = self.get_channel_object("state")

        self.px1env_hwobj = self.getObjectByRole("environment")

        self.frontend_hwobj = self.getObjectByRole("frontend")

        self.lightarm_hwobj = self.getObjectByRole("lightarm")

        self.mxlocal_object = self.getObjectByRole("beamline_configuration")

        self.img2jpeg = self.getProperty("imgtojpeg")
        undulators = self.get_undulators()

        self.exp_type_dict = {"Mesh": "raster", "Helical": "Helical"}

        det_px, det_py = HWR.beamline.detector.get_pixel_size()
        beam_div_hor, beam_div_ver = HWR.beamline.beam.get_beam_divergence()

        self.set_beamline_configuration(
            synchrotron_name="SOLEIL",
            directory_prefix=self.getProperty("directory_prefix"),
            default_exposure_time=HWR.beamline.detector.get_default_exposure_time(),
            minimum_exposure_time=HWR.beamline.detector.get_minimum_exposure_time(),
            detector_fileext=HWR.beamline.detector.get_file_suffix(),
            detector_type=HWR.beamline.detector.get_detector_type(),
            detector_manufacturer=HWR.beamline.detector.get_manufacturer(),
            detector_model=HWR.beamline.detector.get_model(),
            detector_px=det_px,
            detector_py=det_py,
            undulators=undulators,
            focusing_optic=self.getProperty("focusing_optic"),
            monochromator_type=self.getProperty("monochromator"),
            beam_divergence_vertical=beam_div_ver,
            beam_divergence_horizontal=beam_div_hor,
            polarisation=self.getProperty("polarisation"),
            input_files_server=self.getProperty("input_files_server"),
        )

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    def data_collection_hook(self):
        """Main collection hook
        """

        collection_type = self.current_dc_parameters["experiment_type"]

        logging.getLogger("HWR").info(
            "PX1Collect: Running PX1 data collection hook. Type is %s" % collection_type
        )

        if self.aborted_by_user:
            self.emit_collection_failed("Aborted by user")
            self.aborted_by_user = False
            return

        ready = self.prepare_devices_for_collection()

        if not ready:
            self.collection_failed("Cannot prepare collection")
            self.stop_collect()
            return

        if collection_type != "Characterization":  # standard
            prepare_ok = self.prepare_standard_collection()
        else:
            prepare_ok = self.prepare_characterization()

        self._collecting = True

        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]
        # for progressBar brick
        self.emit("progressInit", "Collection", osc_seq["number_of_images"])

        #
        # Run
        #

        self.prepare_directories()

        if collection_type != "Characterization":  # standard
            self.start_standard_collection()
            self.follow_collection_progress()
        else:
            self.start_characterization()

        # includes

        self.data_collection_end()
        self.collection_finished()

    def prepare_standard_collection(self):

        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]
        fileinfo = self.current_dc_parameters["fileinfo"]
        basedir = fileinfo["directory"]

        logging.getLogger("HWR").info("PX1Collect: fileinfo is %s " % str(fileinfo))
        imgname = fileinfo["template"] % osc_seq["start_image_number"]

        # move omega to start angle
        start_angle = osc_seq["start"]

        nb_images = osc_seq["number_of_images"]
        osc_range = osc_seq["range"]
        exp_time = osc_seq["exposure_time"]

        logging.getLogger("HWR").info(
            "PX1Collect:  nb_images: %s / osc_range: %s / exp_time: %s"
            % (nb_images, osc_range, exp_time)
        )

        self.collect_device.exposurePeriod = exp_time
        self.collect_device.numberOfImages = nb_images
        self.collect_device.imageWidth = osc_range

        # self.collect_device.collectAxis = "Omega"

        self.collect_device.startAngle = start_angle
        self.collect_device.triggerMode = 2

        self.collect_device.imagePath = basedir
        self.collect_device.imageName = imgname
        time.sleep(0.2)
        self.collect_device.PrepareCollect()
        ret = self.wait_collect_standby()
        if ret is False:
            logging.getLogger("user_level_log").info(
                "Collect server prepare error. Aborted"
            )
            return False

        self.prepare_headers()

        return True

    def start_standard_collection(self):
        self.emit("collectStarted", (self.owner, 1))
        HWR.beamline.detector.start_collection()
        self.collect_device.Start()

    def follow_collection_progress(self):

        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]
        fileinfo = self.current_dc_parameters["fileinfo"]
        basedir = fileinfo["directory"]
        archive_dir = fileinfo["archive_directory"]
        template = fileinfo["template"]

        jpeg_template = os.path.splitext(template)[0] + ".jpeg"
        thumb_template = os.path.splitext(template)[0] + ".thumb.jpeg"

        osc_range = osc_seq["range"]
        osc_start = osc_seq["start"]
        nb_images = osc_seq["number_of_images"]

        first_imgno = osc_seq["start_image_number"]
        first_image_fullpath = os.path.join(basedir, template % first_imgno)
        first_image_jpegpath = os.path.join(archive_dir, jpeg_template % first_imgno)
        first_image_thumbpath = os.path.join(archive_dir, thumb_template % first_imgno)

        last_imgno = first_imgno + nb_images - 1
        last_image_fullpath = os.path.join(basedir, template % last_imgno)
        last_image_jpegpath = os.path.join(archive_dir, jpeg_template % last_imgno)
        last_image_thumbpath = os.path.join(archive_dir, thumb_template % last_imgno)

        # wait for first image
        self.adxv_latest_refresh = 0
        self.is_firstimg = True

        self.file_waiting_display = first_image_fullpath  # for showing on adxv
        self.wait_image_on_disk(first_image_fullpath)
        thumbs_up = self.generate_thumbnails(
            first_image_fullpath, first_image_jpegpath, first_image_thumbpath
        )
        if thumbs_up:
            self.store_image_in_lims(first_imgno)

        # update display while collect is running
        while self.is_moving() or self.is_firstimg:
            self.adxv_show_latest(fileinfo)
            time.sleep(0.1)

        # wait for last image
        self.wait_image_on_disk(last_image_fullpath)
        thumbs_up = self.generate_thumbnails(
            last_image_fullpath, last_image_jpegpath, last_image_thumbpath
        )
        self.adxv_sync_image(first_image_fullpath)
        if thumbs_up:
            self.store_image_in_lims(last_imgno)

    def prepare_characterization(self):
        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]
        fileinfo = self.current_dc_parameters["fileinfo"]

        basedir = fileinfo["directory"]

        merged_images = self.characterization_nb_merged_images

        osc_range = float(osc_seq["range"]) / merged_images
        exp_time = float(osc_seq["exposure_time"]) / merged_images

        self.collect_device.numberOfImages = int(merged_images)
        self.collect_device.exposurePeriod = exp_time
        self.collect_device.imagePath = basedir
        self.collect_device.imageWidth = osc_range

        HWR.beamline.detector.set_image_headers(["Angle_increment %.4f" % osc_range])

        return True

    def start_characterization(self):

        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]
        fileinfo = self.current_dc_parameters["fileinfo"]

        start_angle = osc_seq["start"]
        nb_images = osc_seq["number_of_images"]
        merged_images = self.characterization_nb_merged_images
        wedge_range = osc_seq["range"] / merged_images

        image_template = fileinfo["template"]

        oscil_image_template = image_template[:3] + "_wdg" + image_template[3:]

        start = start_angle

        self.emit("collectStarted", (self.owner, 1))

        for imgno in range(nb_images):
            image_filename = image_template % (imgno + 1)
            image_fullpath = os.path.join(fileinfo["directory"], image_filename)

            series_first_image = oscil_image_template % (
                (start - start_angle) / wedge_range + 1
            )
            series_last_image = oscil_image_template % (
                (start - start_angle) / wedge_range + merged_images
            )
            series_last_fullpath = os.path.join(
                fileinfo["directory"], series_last_image
            )

            logging.info(
                "PX1Collect: start image series for angle %s - first image name is %s"
                % (start, series_first_image)
            )

            self.collect_device.imageName = series_first_image
            self.collect_device.startAngle = start
            self.wait_collect_ready()
            self.collect_device.prepareCollect()
            self.wait_collect_ready()

            HWR.beamline.detector.set_image_headers(["Start_angle %.4f" % start])
            self.collect_device.Start()

            # file names to wait for

            # wait for completion
            self.wait_collect_ready()
            logging.info(
                "PX1Collect:   waiting to finish image series for angle %s - waiting for %s"
                % (start, series_last_fullpath)
            )
            self.wait_image_on_disk(series_last_fullpath)
            self.adxv_sync_image(series_last_fullpath)

            # merge images into one image
            merge_images(
                series_first_image,
                image_filename,
                fileinfo["directory"],
                start,
                osc_seq["range"],
                osc_seq["exposure_time"],
            )

            logging.info(
                "PX1Collect:   waiting for merged image to appear on disk %s - waiting for %s"
                % (start, image_fullpath)
            )
            self.wait_image_on_disk(image_fullpath)
            self.adxv_sync_image(image_fullpath)

            start += 90.0

    def data_collection_end(self):
        #
        # data collection end (or abort)
        #
        logging.getLogger("HWR").info("PX1Collect: finishing data collection ")
        HWR.beamline.diffractometer.omega.stop()
        HWR.beamline.fast_shutter.closeShutter()

        self.emit("progressStop")

    def data_collection_failed(self):
        logging.getLogger("HWR").info(
            "PX1Collect: Data collection failed. recovering sequence should go here"
        )

    def collect_finished(self, green):
        logging.info("PX1Collect: Data collection finished")

    def collect_failed(self, par):
        logging.exception("PX1Collect: Data collection failed")
        self.current_dc_parameters["status"] = "failed"
        exc_type, exc_value, exc_tb = sys.exc_info()
        failed_msg = "Data collection failed!\n%s" % exc_value
        self.emit(
            "collectOscillationFailed",
            (
                self.owner,
                False,
                failed_msg,
                self.current_dc_parameters.get("collection_id"),
                1,
            ),
        )

        HWR.beamline.detector.stop_collection()
        HWR.beamline.diffractometer.omega.stop()
        self.data_collection_end()

    def set_helical_pos(self, arg):
        """
        Descript. : 8 floats describe
        p1AlignmY, p1AlignmZ, p1CentrX, p1CentrY
        p2AlignmY, p2AlignmZ, p2CentrX, p2CentrY
        """
        self.helical_positions = [
            arg["1"]["phiy"],
            arg["1"]["phiz"],
            arg["1"]["sampx"],
            arg["1"]["sampy"],
            arg["2"]["phiy"],
            arg["2"]["phiz"],
            arg["2"]["sampx"],
            arg["2"]["sampy"],
        ]

    def setMeshScanParameters(self, num_lines, num_images_per_line, mesh_range):
        """
        Descript. :
        """
        pass

    def trigger_auto_processing(self, *args):
        pass

    ## generate snapshots and data thumbnails ##
    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. :
        """
        if not self.is_sampleview_phase():
            self.go_to_sampleview()
            time.sleep(2)  # allow time to refresh display after

        self.lightarm_hwobj.adjustLightLevel()
        time.sleep(0.3)  # allow time to refresh display after

        HWR.beamline.sample_view.save_snapshot(filename)
        logging.getLogger("HWR").debug("PX1Collect:  - snapshot saved to %s" % filename)

    def generate_thumbnails(self, filename, jpeg_filename, thumbnail_filename):
        #
        # write info on LIMS

        try:
            logging.info("PX1Collect: Generating thumbnails for %s" % filename)
            logging.info("PX1Collect:       jpeg file: %s" % jpeg_filename)
            logging.info("PX1Collect:  thumbnail file: %s" % thumbnail_filename)

            self.wait_image_on_disk(filename)
            if os.path.exists(filename):
                subprocess.Popen([self.img2jpeg, filename, jpeg_filename, "0.4"])
                subprocess.Popen([self.img2jpeg, filename, thumbnail_filename, "0.1"])
                return True
            else:
                logging.info(
                    "PX1Collect: Oopps.  Trying to generate thumbs but  image is not on disk"
                )
                return False
        except BaseException:
            import traceback

            logging.error("PX1Collect: Cannot generate thumbnails for %s" % filename)
            logging.error(traceback.format_exc())
            return False

    ## generate snapshots and data thumbnails (END) ##

    ## FILE SYSTEM ##
    def wait_image_on_disk(self, filename, timeout=20.0):
        start_wait = time.time()
        while not os.path.exists(filename):
            if time.time() - start_wait > timeout:
                logging.info("PX1Collect: Giving up waiting for image. Timeout")
                break
            time.sleep(0.1)
        logging.info(
            "PX1Collect: Waiting for image %s ended in  %3.2f secs"
            % (filename, time.time() - start_wait)
        )

    def check_directory(self, basedir):
        if not os.path.exists(basedir):
            try:
                os.makedirs(basedir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    def prepare_directories(self):
        fileinfo = self.current_dc_parameters["fileinfo"]
        basedir = fileinfo["directory"]
        process_dir = basedir.replace("RAW_DATA", "PROCESSED_DATA")

        try:
            os.chmod(process_dir, 0o777)
        except BaseException:
            import traceback

            logging.getLogger("HWR").error(
                "PX1Collect: Error changing permissions for PROCESS directory"
            )
            logging.getLogger("HWR").error(traceback.format_exc())

        self.create_goimg_file(process_dir)

    def create_goimg_file(self, dirname):

        db_f = os.path.join(self.goimg_dir, self.goimg_filename)
        if os.path.exists(db_f):
            os.remove(db_f)

        with open(db_f, "w") as fd:
            fd.write(dirname)
        os.chmod(db_f, 0o777)

    def create_file_directories(self):
        """
        Method create directories for raw files and processing files.
        Directorie for xds.input and auto_processing are created
        """
        self.create_directories(
            self.current_dc_parameters["fileinfo"]["directory"],
            self.current_dc_parameters["fileinfo"]["process_directory"],
        )

        """create processing directories and img links"""
        xds_directory, auto_directory = self.prepare_input_files()
        try:
            # self.create_directories(xds_directory, auto_directory)
            # os.system("chmod -R 777 %s %s" % (xds_directory, auto_directory))
            """todo, create link of imgs for auto_processing
            try:
                os.symlink(files_directory, os.path.join(process_directory, "img"))
            except os.error, e:
                if e.errno != errno.EEXIST:
                    raise
            """
            pass
            # os.symlink(files_directory, os.path.join(process_directory, "img"))
        except BaseException:
            logging.exception("PX1Collect: Could not create processing file directory")
            return

        if xds_directory:
            self.current_dc_parameters["xds_dir"] = xds_directory

        if auto_directory:
            self.current_dc_parameters["auto_dir"] = auto_directory

    def prepare_input_files(self):
        """
        Descript. :
        """
        i = 1
        log = logging.getLogger("user_level_log")
        while True:
            xds_input_file_dirname = "xds_%s_%s_%d" % (
                self.current_dc_parameters["fileinfo"]["prefix"],
                self.current_dc_parameters["fileinfo"]["run_number"],
                i,
            )
            xds_directory = os.path.join(
                self.current_dc_parameters["fileinfo"]["process_directory"],
                xds_input_file_dirname,
            )
            if not os.path.exists(xds_directory):
                break
            i += 1
        self.current_dc_parameters["xds_dir"] = xds_directory

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (
            self.current_dc_parameters["fileinfo"]["prefix"],
            self.current_dc_parameters["fileinfo"]["run_number"],
            i,
        )
        mosflm_directory = os.path.join(
            self.current_dc_parameters["fileinfo"]["process_directory"],
            mosflm_input_file_dirname,
        )

        log.info("  - xds: %s / mosflm: %s" % (xds_directory, mosflm_directory))
        return xds_directory, mosflm_directory

    ## FILE SYSTEM (END) ##

    def prepare_devices_for_collection(self):

        fileinfo = self.current_dc_parameters["fileinfo"]
        basedir = fileinfo["directory"]

        self.check_directory(basedir)

        # check fast shutter closed. others opened
        shutok = self.check_shutters()
        shutok = True

        if not shutok:
            logging.getLogger("user_level_log").info(
                " Shutters not ready for collection. Aborted"
            )
            return False

        detok = HWR.beamline.detector.prepare_collection(self.current_dc_parameters)
        if not detok:
            logging.getLogger("user_level_log").info(
                "Cannot prepare detector for collection. Aborted"
            )
            return False

        adxv_ok = self.adxv_connect()

        diff_ok = self.diffractometer_prepare_collection()
        if not diff_ok:
            logging.getLogger("user_level_log").info(
                "Cannot prepare diffractometer for collection. Aborted"
            )
            return False

        return True

    def diffractometer_prepare_collection(self):
        HWR.beamline.diffractometer.wait_device_ready(timeout=10)

        # go to collect phase
        if not self.is_collect_phase():
            success = self.go_to_collect()
            if not success:
                logging.getLogger("HWR").info("PX1Collect: Cannot set COLLECT phase")
                return False
        return True

    def prepare_headers(self):
        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]

        ax, ay, bx, by = self.get_beam_configuration()

        dist = HWR.beamline.detector.distance.get_value()
        wavlen = HWR.beamline.energy.get_wavelength()

        start_angle = osc_seq["start"]
        nb_images = osc_seq["number_of_images"]
        img_range = osc_seq["range"]
        exp_time = osc_seq["exposure_time"]

        kappa_angle = HWR.beamline.diffractometer.kappa.get_value()

        _settings = [
            ["Wavelength %.5f", wavlen],
            ["Detector_distance %.4f", dist / 1000.0],
            ["Beam_x %.2f", ax * dist + bx],
            ["Beam_y %.2f", ay * dist + by],
            ["Alpha %.2f", 49.64],
            ["Start_angle %.4f", start_angle],
            ["Angle_increment %.4f", img_range],
            ["Oscillation_axis %s", "Omega"],
            ["Detector_2theta %.4f", 0.0],
            ["Polarization %.3f", 0.990],
            ["Kappa %.4f", kappa_angle],
        ]

        # if self.oscaxis == "Phi":
        # _settings.append(["Chi %.4f", self.omega_hwo.get_value()])
        # _settings.append(["Phi %.4f", start])
        # elif self.oscaxis == "Omega":
        _settings.append(
            ["Phi %.4f", HWR.beamline.diffractometer.kappa_phi.get_value()]
        )
        _settings.append(["Chi %.4f", start_angle])
        HWR.beamline.detector.set_image_headers(_settings)

    def check_shutters(self):
        # Check safety shutter
        if self.check_shutter_opened(
            HWR.beamline.safety_shutter, "Safety shutter"
        ) and self.check_shutter_opened(self.frontend_hwobj, "Front end"):
            return True
        else:
            return False

    def check_shutter_opened(self, shut_hwo, shutter_name="shutter"):
        if shut_hwo.isShutterOpened():
            return True

        if shut_hwo.get_state() == "disabled":
            logging.getLogger("user_level_log").warning(
                "%s disabled. Collect cancelled" % shutter_name
            )
            return False
        elif shut_hwo.get_state() in ["fault", "alarm", "error"]:
            logging.getLogger("user_level_log").warning(
                "%s is in fault state. Collect cancelled" % shutter_name
            )
            return False
        elif shut_hwo.isShutterClosed():
            shut_hwo.openShutter()
            return shut_hwo.waitShutter("opened")
        else:
            logging.getLogger("user_level_log").warning(
                "%s is in an unhandled state. Collect cancelled" % shutter_name
            )
            return False

    def close_fast_shutter(self):
        HWR.beamline.fast_shutter.closeShutter()

    def close_safety_shutter(self):
        pass

    ## COLLECT SERVER STATE ##
    def wait_collect_standby(self, timeout=10):
        t0 = time.time()
        while not self.is_standby():
            elapsed = time.time() - t0
            if elapsed > timeout:
                break
            time.sleep(0.1)

    def wait_collect_moving(self, timeout=10):
        t0 = time.time()
        while not self.is_moving():
            elapsed = time.time() - t0
            if elapsed > timeout:
                break
            time.sleep(0.1)

    def wait_collect_ready(self, timeout=10):
        t0 = time.time()
        while self.is_moving():
            elapsed = time.time() - t0
            if elapsed > timeout:
                break
            time.sleep(0.1)

    def is_standby(self):
        return str(self.collect_state_chan.getValue()) == "STANDBY"

    def is_moving(self):
        return str(self.collect_state_chan.getValue()) in ["MOVING", "RUNNING"]

    ## COLLECT SERVER STATE (END) ##

    ## PX1 ENVIRONMENT PHASE HANDLING ##
    def is_collect_phase(self):
        return self.px1env_hwobj.isPhaseCollect()

    def go_to_collect(self, timeout=180):
        self.px1env_hwobj.gotoCollectPhase()
        gevent.sleep(0.5)

        t0 = time.time()
        while True:
            env_state = self.px1env_hwobj.get_state()
            if env_state != "RUNNING" and self.is_collect_phase():
                break
            if time.time() - t0 > timeout:
                logging.getLogger("HWR").debug(
                    "PX1Collect: timeout sending supervisor to collect phase"
                )
                break
            gevent.sleep(0.5)

        return self.px1env_hwobj.isPhaseCollect()

    def is_sampleview_phase(self):
        return self.px1env_hwobj.isPhaseVisuSample()

    def go_to_sampleview(self, timeout=180):
        self.px1env_hwobj.gotoSampleViewPhase()

        gevent.sleep(0.5)

        t0 = time.time()
        while True:
            env_state = self.px1env_hwobj.get_state()
            if env_state != "RUNNING" and self.is_sampleview_phase():
                break
            if time.time() - t0 > timeout:
                logging.getLogger("HWR").debug(
                    "PX1Collect: timeout sending supervisor to sample view phase"
                )
                break
            gevent.sleep(0.5)

        self.lightarm_hwobj.adjustLightLevel()
        return self.is_sampleview_phase()

    ## PX1 ENVIRONMENT PHASE HANDLING (END) ##

    @task
    def move_motors(self, motor_position_dict):
        """
        Descript. :
        """
        HWR.beamline.diffractometer.move_motors(motor_position_dict)

    def get_undulators_gaps(self):
        """
        Descript. : return gaps as dict. In our case we have one gap,
                    others are 0
        """
        if HWR.beamline.energy:
            try:
                u20_gap = HWR.beamline.energy.getCurrentUndulatorGap()
                return {"u20": u20_gap}
            except BaseException:
                return {}
        else:
            return {}

    def get_slit_gaps(self):
        """
        Descript. :
        """
        if HWR.beamline.beam is not None:
            return HWR.beamline.beam.get_slits_gap()
        return None, None

    def get_beam_shape(self):
        """
        Descript. :
        """
        if HWR.beamline.beam is not None:
            return HWR.beamline.beam.get_beam_shape()

    def get_machine_current(self):
        """
        Descript. :
        """
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.get_current()
        else:
            return 0

    def get_machine_message(self):
        """
        Descript. :
        """
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.get_message()
        else:
            return ""

    def get_machine_fill_mode(self):
        """
        Descript. :
        """
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.get_fill_mode()
        else:
            return ""

    def get_beam_configuration(self):
        pars_beam = self.mxlocal_object["SPEC_PARS"]["beam"]
        ax = pars_beam.getProperty("ax")
        ay = pars_beam.getProperty("ay")
        bx = pars_beam.getProperty("bx")
        by = pars_beam.getProperty("by")
        return [ax, ay, bx, by]

    def get_undulators(self):
        return [U20()]

    ## OTHER HARDWARE OBJECTS (END) ##

    ## ADXV display images ##
    def adxv_connect(self):

        #  connect every time?? maybe we can do better
        try:
            res = socket.getaddrinfo(
                self.adxv_host, self.adxv_port, 0, socket.SOCK_STREAM
            )
            af, socktype, proto, canonname, sa = res[0]
            self.adxv_socket = socket.socket(af, socktype, proto)
            self.adxv_socket.connect((self.adxv_host, self.adxv_port))
            logging.getLogger().info("PX1Collect: ADXV Visualization connected.")
        except BaseException:
            self.adxv_socket = None
            logging.getLogger().info("PX1Collect: WARNING: Can't connect to ADXV.")

    def adxv_show_latest(self, fileinfo):

        now = time.time()
        elapsed = now - self.adxv_latest_refresh

        template = fileinfo["template"]
        basedir = fileinfo["directory"]

        if self.file_waiting_display is not None:
            if os.path.exists(self.file_waiting_display):
                self.adxv_sync_image(self.file_waiting_display)
                self.file_waiting_display = None
                self.is_firstimg = False

        # find next file to display
        if elapsed >= self.adxv_interval and self.file_waiting_display is None:
            _current_img_no = self.collect_device.currentImageSpi
            self.file_waiting_display = os.path.join(
                basedir, template % _current_img_no
            )
            self.adxv_last_refresh = time.time()

    def adxv_sync_image(self, filename):

        adxv_send_cmd = "\nload_image %s\n" + chr(32)

        try:
            if not self.adxv_socket:
                try:
                    self.adxv_connect()
                except Exception as err:
                    self.adxv_socket = None
                    logging.info(
                        "PX1Collect: ADXV: Warning: Can't connect to adxv socket to follow collect."
                    )
                    logging.error("PX1Collect: ADXV0: msg= %s" % err)
            else:
                logging.info(("PX1Collect: ADXV: " + adxv_send_cmd[1:-2]) % imgname)
                self.adxv_socket.send(adxv_send_cmd % imgname)
        except BaseException:
            try:
                del self.adxv_socket
                self.adxv_connect()
            except Exception as err:
                self.adxv_socket = None
                logging.error("PX1Collect: ADXV1: msg= %s" % err)

    ## ADXV display images (END) ##


class U20(object):
    def __init__(self):
        self.type = "u20"


def test_hwo(hwo):
    print("PX1Environemnt (collect phase): ", hwo.is_collect_phase())
    print("Shutters (ready for collect): ", hwo.check_shutters())
    print("is collect? ", hwo.is_collect_phase())
    print("is samplevisu? ", hwo.is_sampleview_phase())
    print("goint to sample visu")
    hwo.go_to_sampleview()
    # print "goint to collect"
    # hwo.go_to_collect()
    print("is collect? ", hwo.is_collect_phase())
    print("is samplevisu? ", hwo.is_sampleview_phase())
