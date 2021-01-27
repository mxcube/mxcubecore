#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
ALBACollect
"""
import os
import time
import logging
import sys
import gevent
from mxcubecore.TaskUtils import task
from mxcubecore.hardware_objects.abstract.AbstractCollect import AbstractCollect
from mxcubecore import HardwareRepository as HWR


__author__ = "Vicente Rey Bakaikoa"
__credits__ = ["MXCuBE collaboration"]
__version__ = "2.2."


class ALBACollect(AbstractCollect):
    """Main data collection class. Inherited from AbstractMulticollect
       Collection is done by setting collection parameters and
       executing collect command
    """

    def __init__(self, name):
        """

        :param name: name of the object
        :type name: string
        """

        AbstractCollect.__init__(self, name)
        #        HardwareObject.__init__(self, name)

        self._error_msg = ""
        self.owner = None
        self.osc_id = None
        self._collecting = None

        self.helical_positions = None
        self.saved_omega_velocity = None

    def init(self):
        """
        Init method
        """

        self.ready_event = gevent.event.Event()

        self.supervisor_hwobj = self.get_object_by_role("supervisor")

        self.slowshut_hwobj = self.get_object_by_role("slow_shutter")
        self.photonshut_hwobj = self.get_object_by_role("photon_shutter")
        self.frontend_hwobj = self.get_object_by_role("frontend")

        self.ni_conf_cmd = self.get_command_object("ni_configure")
        self.ni_unconf_cmd = self.get_command_object("ni_unconfigure")

        # some extra reading channels to be saved in image header
        self.kappapos_chan = self.get_channel_object("kappapos")
        self.phipos_chan = self.get_channel_object("phipos")

        undulators = []
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except Exception:
            pass

        self.exp_type_dict = {"Mesh": "raster", "Helical": "Helical"}

        det_px, det_py = HWR.beamline.detector.get_pixel_size()
        beam_div_hor, beam_div_ver = HWR.beamline.beam.get_beam_divergence()

        self.set_beamline_configuration(
            synchrotron_name="ALBA",
            directory_prefix=self.get_property("directory_prefix"),
            default_exposure_time=HWR.beamline.detector.get_default_exposure_time(),
            minimum_exposure_time=HWR.beamline.detector.get_minimum_exposure_time(),
            detector_fileext=HWR.beamline.detector.get_file_suffix(),
            detector_type=HWR.beamline.detector.get_detector_type(),
            detector_manufacturer=HWR.beamline.detector.get_manufacturer(),
            detector_model=HWR.beamline.detector.get_model(),
            detector_px=det_px,
            detector_py=det_py,
            undulators=undulators,
            focusing_optic=self.get_property("focusing_optic"),
            monochromator_type=self.get_property("monochromator"),
            beam_divergence_vertical=beam_div_ver,
            beam_divergence_horizontal=beam_div_hor,
            polarisation=self.get_property("polarisation"),
            input_files_server=self.get_property("input_files_server"),
        )

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    def data_collection_hook(self):
        """Main collection hook
        """

        logging.getLogger("HWR").info("Running ALBA data collection hook")

        logging.getLogger("HWR").info("  -- wait for devices to finish moving --")
        logging.getLogger("HWR").info("       + wait for resolution...")
        HWR.beamline.resolution.wait_end_of_move()
        logging.getLogger("HWR").info("       + wait for detector distance...")
        HWR.beamline.detector.wait_move_distance_done()
        logging.getLogger("HWR").info("       + wait for energy...")
        HWR.beamline.energy.wait_move_energy_done()

        if self.aborted_by_user:
            self.emit_collection_failed("Aborted by user")
            self.aborted_by_user = False
            return

        ### EDNA_REF, OSC, MESH, HELICAL

        exp_type = self.current_dc_parameters["experiment_type"]
        logging.getLogger("HWR").debug("Running a collect (exp_type=%s)" % exp_type)

        if exp_type == "Characterization":
            logging.getLogger("HWR").debug("Running a collect (CHARACTERIZATION)")
        elif exp_type == "Helical":
            logging.getLogger("HWR").debug("Running a helical collection")
            logging.getLogger("HWR").debug(
                "   helical positions are: %s" % str(self.helical_positions)
            )
            hpos = self.helical_positions
            logging.getLogger("HWR").debug(
                "               phiy from %3.4f to %3.4f" % (hpos[0], hpos[4])
            )
            logging.getLogger("HWR").debug(
                "               phiz from %3.4f to %3.4f" % (hpos[1], hpos[5])
            )
            logging.getLogger("HWR").debug(
                "              sampx from %3.4f to %3.4f" % (hpos[2], hpos[6])
            )
            logging.getLogger("HWR").debug(
                "              sampy from %3.4f to %3.4f" % (hpos[3], hpos[7])
            )
        elif exp_type == "Mesh":
            logging.getLogger("HWR").debug("Running a raster collection ()")
            logging.getLogger("HWR").debug(
                "   number of lines are: %s" % self.mesh_num_lines
            )
            logging.getLogger("HWR").debug(
                "   total nb of frames: %s" % self.mesh_total_nb_frames
            )
            logging.getLogger("HWR").debug(
                "          mesh range : %s" % self.mesh_range
            )
            logging.getLogger("HWR").debug(
                "          mesh center : %s" % self.mesh_center
            )
        else:
            logging.getLogger("HWR").debug("Running a collect (STANDARD)")

        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]

        image_range = osc_seq["range"]
        nb_images = osc_seq["number_of_images"]
        total_range = image_range * nb_images

        ready = self.prepare_acquisition()

        if not ready:
            self.collection_failed("Cannot prepare collection")
            self.stop_collect()
            return

        self._collecting = True
        # for progressBar brick
        self.emit("progressInit", "Collection", osc_seq["number_of_images"])

        omega_pos = osc_seq["start"]

        logging.getLogger("HWR").info("Starting detector")
        self.emit("collectStarted", (self.owner, 1))

        first_image_no = osc_seq["start_image_number"]

        if exp_type == "OSC" or (exp_type == "Characterization" and nb_images == 1):
            final_pos = self.prepare_collection(
                start_angle=omega_pos,
                nb_images=nb_images,
                first_image_no=first_image_no,
            )
            HWR.beamline.detector.start_collection()
            self.collect_images(final_pos, nb_images, first_image_no)
        elif exp_type == "Characterization" and nb_images > 1:  # image one by one
            for imgno in range(nb_images):
                final_pos = self.prepare_collection(
                    start_angle=omega_pos, nb_images=1, first_image_no=first_image_no
                )
                HWR.beamline.detector.start_collection()
                self.collect_images(final_pos, 1, first_image_no)
                first_image_no += 1
                omega_pos += 90

    def collect_images(self, final_pos, nb_images, first_image_no):
        #
        # Run
        #
        logging.getLogger("HWR").info(
            "collecting images, by moving omega to %s" % final_pos
        )
        HWR.beamline.diffractometer.omega.set_value(final_pos)
        self.wait_collection_done(nb_images, first_image_no)
        self.data_collection_end()
        self.collection_finished()

    def data_collection_end(self):
        HWR.beamline.fast_shutter.cmdOut()
        HWR.beamline.diffractometer.omega.set_velocity(60)
        self.unconfigure_ni()

    def data_collection_failed(self):
        logging.getLogger("HWR").info(
            "Data collection failed. recovering sequence should go here"
        )

    def prepare_acquisition(self):

        fileinfo = self.current_dc_parameters["fileinfo"]

        basedir = fileinfo["directory"]

        #  save omega velocity
        self.saved_omega_velocity = HWR.beamline.diffractometer.omega.get_velocity()

        # create directories if needed
        self.check_directory(basedir)

        # check fast shutter closed. others opened
        shutok = self.check_shutters()

        if not shutok:
            logging.getLogger("user_level_log").error(
                " Shutters are not ready. BYPASSED. Comment line in ALBACollect.py"
            )
        else:
            logging.getLogger("user_level_log").error(
                " Shutters ready but code is BYPASSED. Comment line in ALBACollect.py"
            )

        shutok = True  # DELETE THIS AFTER TESTS

        if not shutok:
            logging.getLogger("user_level_log").error(" Shutters not ready")
            return False

        gevent.sleep(1)
        logging.getLogger("HWR").info(
            " Waiting for diffractometer to be ready. Now %s"
            % str(HWR.beamline.diffractometer.current_state)
        )
        HWR.beamline.diffractometer.wait_device_ready(timeout=10)
        logging.getLogger("HWR").info("             diffractometer is now ready.")

        # go to collect phase
        if not self.is_collect_phase():
            logging.getLogger("HWR").info(
                " Not in collect phase. Asking supervisor to go"
            )
            logging.getLogger("HWR").info(
                "  diffractometer is now ready. Now %s"
                % str(HWR.beamline.diffractometer.current_state)
            )
            success = self.go_to_collect()
            if not success:
                logging.getLogger("user_level_log").error(
                    "Cannot set COLLECT phase for diffractometer"
                )
                return False

        detok = HWR.beamline.detector.prepare_acquisition(self.current_dc_parameters)

        return detok

    def prepare_collection(self, start_angle, nb_images, first_image_no):
        # move omega to start angle
        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]

        # start_angle = osc_seq['start']
        # nb_images = osc_seq['number_of_images']

        img_range = osc_seq["range"]
        exp_time = osc_seq["exposure_time"]

        total_dist = nb_images * img_range
        total_time = nb_images * exp_time
        omega_speed = float(total_dist / total_time)

        logging.getLogger("HWR").info("  prepare detector  was not ok.")
        self.write_image_headers(start_angle)

        logging.getLogger("HWR").info(
            "  nb_images: %s / img_range: %s / exp_time: %s / total_distance: %s / speed: %s"
            % (nb_images, img_range, exp_time, total_dist, omega_speed)
        )
        logging.getLogger("HWR").info(
            "  setting omega velocity to 60 to go to intial position"
        )
        HWR.beamline.diffractometer.omega.set_velocity(60)

        omega_acceltime = HWR.beamline.diffractometer.omega.get_acceleration()

        safe_delta = 9.0 * omega_speed * omega_acceltime

        init_pos = start_angle - safe_delta
        final_pos = start_angle + total_dist + safe_delta

        logging.getLogger("HWR").info("Moving omega to initial position %s" % init_pos)
        HWR.beamline.diffractometer.omega.set_value(init_pos)

        HWR.beamline.detector.prepare_collection(nb_images, first_image_no)

        HWR.beamline.diffractometer.omega.wait_end_of_move(timeout=10)

        logging.getLogger("HWR").info(
            "Moving omega finished at %s"
            % HWR.beamline.diffractometer.omega.get_value()
        )

        # program omega speed depending on exposure time

        logging.getLogger("HWR").info("Setting omega velocity to %s" % omega_speed)
        HWR.beamline.diffractometer.omega.set_velocity(omega_speed)
        if omega_speed != 0:
            self.configure_ni(start_angle, total_dist)

        return final_pos

    def write_image_headers(self, start_angle):
        fileinfo = self.current_dc_parameters["fileinfo"]
        basedir = fileinfo["directory"]

        exp_type = self.current_dc_parameters["experiment_type"]
        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]

        nb_images = osc_seq["number_of_images"]
        # start_angle = osc_seq['start']

        img_range = osc_seq["range"]

        if exp_type == "Characterization":
            angle_spacing = 90
        else:
            angle_spacing = img_range

        exp_time = osc_seq["exposure_time"]

        # PROGRAM Image Headers
        # latency_time = 0.003
        latency_time = HWR.beamline.detector.get_latency_time()
        limaexpt = exp_time - latency_time

        self.image_headers = {}

        angle_info = [start_angle, img_range, angle_spacing]

        self.image_headers["nb_images"] = nb_images
        self.image_headers["Exposure_time"] = "%.4f" % limaexpt
        self.image_headers["Exposure_period"] = "%.4f" % exp_time
        self.image_headers["Start_angle"] = "%f deg." % start_angle
        self.image_headers["Angle_increment"] = "%f deg." % img_range
        self.image_headers["Wavelength"] = HWR.beamline.energy.get_wavelength()

        self.image_headers["Detector_distance"] = "%.5f m" % (
            HWR.beamline.detector.distance.get_value() / 1000.0
        )
        self.image_headers["Detector_Voffset"] = "0 m"

        beamx, beamy = HWR.beamline.detector.get_beam_centre()
        self.image_headers["Beam_xy"] = "(%.2f, %.2f) pixels" % (beamx, beamy)

        self.image_headers["Filter_transmission"] = "%.4f" % (
            HWR.beamline.transmission.get_value() / 100.0
        )
        self.image_headers["Flux"] = "%.4g" % HWR.beamline.flux.get_value()
        self.image_headers["Detector_2theta"] = "0.0000"
        self.image_headers["Polarization"] = "0.99"
        self.image_headers["Alpha"] = "0 deg."

        self.image_headers["Kappa"] = "%.4f deg." % self.kappapos_chan.get_value()
        self.image_headers["Phi"] = "%.4f deg." % self.phipos_chan.get_value()

        self.image_headers["Chi"] = "0 deg."
        self.image_headers["Oscillation_axis"] = "X, CW"
        self.image_headers["N_oscillations"] = "1"
        self.image_headers["Detector_2theta"] = "0.0000 deg"

        self.image_headers["Image_path"] = ": %s" % basedir

        self.image_headers["Threshold_setting"] = (
            "%0f eV" % HWR.beamline.detector.get_threshold()
        )
        self.image_headers["Gain_setting"] = "%s" % str(
            HWR.beamline.detector.get_threshold_gain()
        )

        self.image_headers["Tau"] = "%s s" % str(199.1e-09)
        self.image_headers["Count_cutoff"] = "%s counts" % str(370913)
        self.image_headers["N_excluded_pixels"] = "= %s" % str(1178)
        self.image_headers["Excluded_pixels"] = ": %s" % str("badpix_mask.tif")
        self.image_headers["Trim_file"] = ": %s" % str(
            "p6m0108_E12661_T6330_vrf_m0p20.bin"
        )

        HWR.beamline.detector.set_image_headers(self.image_headers, angle_info)

    def wait_collection_done(self, nb_images, first_image_no):

        osc_seq = self.current_dc_parameters["oscillation_sequence"][0]

        # first_image_no = osc_seq['start_image_number']
        # nb_images = osc_seq['number_of_images']
        last_image_no = first_image_no + nb_images - 1

        if nb_images > 1:
            self.wait_save_image(first_image_no)
        HWR.beamline.diffractometer.omega.wait_end_of_move(timeout=720)
        self.wait_save_image(last_image_no)

    def wait_save_image(self, frame_number, timeout=25):

        fileinfo = self.current_dc_parameters["fileinfo"]
        basedir = fileinfo["directory"]
        template = fileinfo["template"]

        filename = template % frame_number
        fullpath = os.path.join(basedir, filename)

        start_wait = time.time()

        logging.getLogger("HWR").debug("   waiting for image on disk: %s", fullpath)

        while not os.path.exists(fullpath):
            dirlist = os.listdir(basedir)  # forces directory flush ?
            if (time.time() - start_wait) > timeout:
                logging.getLogger("HWR").debug("   giving up waiting for image")
                return False
            time.sleep(0.2)

        self.last_saved_image = fullpath

        # generate thumbnails
        archive_dir = fileinfo["archive_directory"]
        self.check_directory(archive_dir)

        jpeg_filename = os.path.splitext(filename)[0] + ".jpeg"
        thumb_filename = os.path.splitext(filename)[0] + ".thumb.jpeg"

        thumb_fullpath = os.path.join(archive_dir, thumb_filename)
        jpeg_fullpath = os.path.join(archive_dir, jpeg_filename)

        logging.getLogger("HWR").debug(
            "   creating thumbnails for  %s in: %s and %s"
            % (fullpath, jpeg_fullpath, thumb_fullpath)
        )
        cmd = "adxv_thumb 0.4 %s %s" % (fullpath, jpeg_fullpath)
        os.system(cmd)
        cmd = "adxv_thumb 0.1 %s %s" % (fullpath, thumb_fullpath)
        os.system(cmd)

        logging.getLogger("HWR").debug("   writing thumbnails info in LIMS")
        self.store_image_in_lims(frame_number)

        return True

    def check_shutters(self):

        # Check fast shutter
        if HWR.beamline.fast_shutter.get_state() != 0:
            return False

        # Check slow shutter
        if self.slowshut_hwobj.get_state() != 1:
            return False

        # Check photon shutter
        if self.photonshut_hwobj.get_state() != 1:
            return False

        # Check front end
        if self.frontend_hwobj.get_state() != 1:
            return False

        return True

    def get_image_headers(self):
        headers = []
        return headers

    def collection_end(self):
        #
        # data collection end (or abort)
        #
        logging.getLogger("HWR").info(" finishing data collection ")
        HWR.beamline.fast_shutter.cmdOut()
        self.emit("progressStop")

    def check_directory(self, basedir):
        if not os.path.exists(basedir):
            try:
                os.makedirs(basedir)
            except OSError as e:
                import errno

                if e.errno != errno.EEXIST:
                    raise

    def collect_finished(self, green):
        logging.info("Data collection finished")

    def collect_failed(self, par):
        logging.exception("Data collection failed")
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

    def go_to_collect(self, timeout=180):
        logging.getLogger("HWR").debug("sending supervisor to collect phase")
        self.supervisor_hwobj.go_collect()
        logging.getLogger("HWR").debug("supervisor sent to collect phase")

        gevent.sleep(0.5)

        t0 = time.time()
        while True:
            super_state = str(self.supervisor_hwobj.get_state()).upper()
            cphase = self.supervisor_hwobj.get_current_phase().upper()
            if super_state != "MOVING" and cphase == "COLLECT":
                break
            if time.time() - t0 > timeout:
                logging.getLogger("HWR").debug(
                    "timeout sending supervisor to collect phase"
                )
                break
            gevent.sleep(0.5)

        logging.getLogger("HWR").debug(
            "supervisor finished go collect phase task. phase is now: %s" % cphase
        )

        return self.is_collect_phase()

    def is_collect_phase(self):
        return self.supervisor_hwobj.get_current_phase().upper() == "COLLECT"

    def go_to_sampleview(self, timeout=180):
        logging.getLogger("HWR").debug("sending supervisor to sample view phase")
        self.supervisor_hwobj.go_sample_view()
        logging.getLogger("HWR").debug("supervisor sent to sample view phase")

        gevent.sleep(0.5)

        t0 = time.time()
        while True:
            super_state = str(self.supervisor_hwobj.get_state()).upper()
            cphase = self.supervisor_hwobj.get_current_phase().upper()
            if super_state != "MOVING" and cphase == "SAMPLE":
                break
            if time.time() - t0 > timeout:
                logging.getLogger("HWR").debug(
                    "timeout sending supervisor to sample view phase"
                )
                break
            gevent.sleep(0.5)

        logging.getLogger("HWR").debug(
            "supervisor finished go sample view phase task. phase is now: %s" % cphase
        )

        return self.is_sampleview_phase()

    def is_sampleview_phase(self):
        return self.supervisor_hwobj.get_current_phase().upper() == "SAMPLE"

    def configure_ni(self, startang, total_dist):
        logging.getLogger("HWR").debug(
            "Configuring NI660 with pars 0, %s, %s, 0, 1" % (startang, total_dist)
        )
        self.ni_conf_cmd(0.0, startang, total_dist, 0, 1)

    def unconfigure_ni(self):
        self.ni_unconf_cmd()

    def open_safety_shutter(self):
        """ implements prepare_shutters in collect macro """

        # prepare ALL shutters

        # close fast shutter
        if HWR.beamline.fast_shutter.get_state() != 0:
            HWR.beamline.fast_shutter.close()

        # open slow shutter
        if self.slowshut_hwobj.get_state() != 1:
            self.slowshut_hwobj.open()

        # open photon shutter
        if self.photonshut_hwobj.get_state() != 1:
            self.photonshut_hwobj.open()

        # open front end
        if self.frontend_hwobj.get_state() != 0:
            self.frontend_hwobj.open()

    def open_detector_cover(self):
        self.supervisor_hwobj.open_detector_cover()

    def open_fast_shutter(self):
        # HWR.beamline.fast_shutter.open()
        #   this function is empty for ALBA. we are not opening the fast shutter.
        #   on the contrary open_safety_shutter (equivalent to prepare_shutters in original
        #   collect macro will first close the fast shutter and open the other three
        pass

    def close_fast_shutter(self):
        HWR.beamline.fast_shutter.cmdOut()

    def close_safety_shutter(self):
        #  we will not close safety shutter during collections
        pass

    def close_detector_cover(self):
        #  we will not close detcover during collections
        #  self.supervisor.close_detector_cover()
        pass

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

    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. :
        """
        if not self.is_sampleview_phase():
            self.go_to_sampleview()

        HWR.beamline.sample_view.save_snapshot(filename)
        logging.getLogger("HWR").debug(" - snapshot saved to %s" % filename)

    @task
    def move_motors(self, motor_position_dict):
        """
        Descript. :
        """
        HWR.beamline.diffractometer.move_motors(motor_position_dict)

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
        xds_directory, auto_directory, ednaproc_directory = self.prepare_input_files()

        try:
            self.create_directories(xds_directory, auto_directory, ednaproc_directory)
            os.system(
                "chmod -R 777 %s %s %s"
                % (xds_directory, auto_directory, ednaproc_directory)
            )
            """todo, create link of imgs for auto_processing
            try:
                os.symlink(files_directory, os.path.join(process_directory, "img"))
            except os.error, e:
                if e.errno != errno.EEXIST:
                    raise
            """
            # os.symlink(files_directory, os.path.join(process_directory, "img"))
        except Exception:
            logging.exception("Could not create processing file directory")
            return

        if xds_directory:
            self.current_dc_parameters["xds_dir"] = xds_directory

        if auto_directory:
            self.current_dc_parameters["auto_dir"] = auto_directory

        # pass wavelength needed in auto processing input files

        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        osc_pars["wavelength"] = HWR.beamline.energy.get_wavelength()

        HWR.beamline.offline_processing.create_input_files(
            xds_directory, auto_directory, self.current_dc_parameters
        )

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

        mosflm_input_file_dirname = "mosflm_%s_%s_%d" % (
            self.current_dc_parameters["fileinfo"]["prefix"],
            self.current_dc_parameters["fileinfo"]["run_number"],
            i,
        )
        mosflm_directory = os.path.join(
            self.current_dc_parameters["fileinfo"]["process_directory"],
            mosflm_input_file_dirname,
        )

        log.info("  - xds: %s / mosflm: %s" % (xds_directory, mosflm_directory))

        while True:
            ednaproc_dirname = "ednaproc_%s_%s_%d" % (
                self.current_dc_parameters["fileinfo"]["prefix"],
                self.current_dc_parameters["fileinfo"]["run_number"],
                i,
            )
            ednaproc_directory = os.path.join(
                self.current_dc_parameters["fileinfo"]["process_directory"],
                ednaproc_dirname,
            )
            if not os.path.exists(ednaproc_directory):
                break
            i += 1

        self.current_dc_parameters["ednaproc_dir"] = ednaproc_directory

        return xds_directory, mosflm_directory, ednaproc_directory

    def get_undulators_gaps(self):
        """
        Descript. : return triplet with gaps. In our case we have one gap,
                    others are 0
        """
        # TODO
        try:
            if self.chan_undulator_gap:
                und_gaps = self.chan_undulator_gap.get_value()
                if type(und_gaps) in (list, tuple):
                    return und_gaps
                else:
                    return und_gaps
        except Exception:
            pass
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
            return "FillMode not/impl"
            # fill_mode = str(self.machine_info_hwobj.get_message())
            # return fill_mode[:20]
        else:
            return ""

    def trigger_auto_processing(self, event, frame):
        if event == "after":
            dc_pars = self.current_dc_parameters
            HWR.beamline.offline_processing.trigger_auto_processing(dc_pars)


def test_hwo(hwo):
    print("Shutters (ready for collect): ", hwo.check_shutters())
    print("Supervisor(collect phase): ", hwo.is_collect_phase())

    print("Kappa ", hwo.kappapos_chan.get_value())
    print("Phi ", hwo.phipos_chan.get_value())
