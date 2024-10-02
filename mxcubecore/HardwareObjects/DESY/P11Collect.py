# encoding: utf-8
#
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

__copyright__ = """Copyright The MXCuBE Collaboration"""
__license__ = "LGPLv3+"

import errno
import socket
import time
import sys
import os
import logging
import traceback
import h5py
import numpy as np
import psutil
import subprocess
import gevent

from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from mxcubecore import HardwareRepository as HWR
from mxcubecore.TaskUtils import task
from mxcubecore.Command.Tango import DeviceProxy

FILE_TIMEOUT = 5


class P11Collect(AbstractCollect):
    def __init__(self, *args):
        super().__init__(*args)

    def init(self):
        """Initializes beamline collection parameters like default speed and server names."""
        super().init()
        self.default_speed = 120 #self.get_property("omega_default_speed", 130)
        self.turnback_time = 0.5# self.get_property("turnback_time", 0.3)
        self.filter_server_name = self.get_property("filterserver")
        self.mono_server_name = self.get_property("monoserver")
        self.filter_server = DeviceProxy(self.filter_server_name)
        self.mono_server = DeviceProxy(self.mono_server_name)

        self.latest_frames = None
        self.acq_speed = None
        self.total_angle_range = None

    @task
    def move_motors(self, motor_position_dict):
        """Moves motors to the specified positions.
        
        Args:
            motor_position_dict (dict): Dictionary containing motor positions.
        """
        HWR.beamline.diffractometer.move_motors(motor_position_dict)

    def _take_crystal_snapshot(self, filename):
        """Takes a snapshot of the crystal and saves it to the given filename.
        
        Args:
            filename (str): Path to save the crystal snapshot.
        
        Raises:
            RuntimeError: If unable to move to the centring phase.
        """
        self.log.debug("#COLLECT# taking crystal snapshot.")

        if not HWR.beamline.diffractometer.is_centring_phase():
            self.log.debug("#COLLECT# take_snapshot. moving to centring phase")
            HWR.beamline.diffractometer.goto_centring_phase(wait=True)

        time.sleep(0.3)
        if not HWR.beamline.diffractometer.is_centring_phase():
            raise RuntimeError(
                "P11Collect. cannot reach centring phase for acquiring snapshots"
            )

        self.log.debug("#COLLECT# saving snapshot to %s" % filename)
        HWR.beamline.sample_view.save_snapshot(filename)

    def set_transmission(self, value):
        """Sets the transmission value on the beamline.
        
        Args:
            value (float): Transmission value to set.
        """
        HWR.beamline.transmission.set_value(value)

    def set_energy(self, value):
        """Sets the energy value on the beamline.
        
        Args:
            value (float): Energy value to set.
        """
        HWR.beamline.energy.set_value(value)
        
    def set_resolution(self, value):
        """Sets the resolution of the beamline.
        
        Args:
            value (float): Resolution value to set.
        """
        if round(HWR.beamline.resolution.get_value(), 2) != round(value, 2):
            HWR.beamline.resolution.set_value(value)

    def do_collect(self, owner):
        """Performs the data collection sequence.
        
        Args:
            owner: Owner of the current data collection.

        Raises:
            RuntimeError: If collection preparation or execution fails.
        """
        log = logging.getLogger("user_level_log")
        log.info("Collection: Preparing to collect")
        self.emit("collectReady", (False,))
        self.emit(
            "collectOscillationStarted",
            (owner, None, None, None, self.current_dc_parameters, None),
        )
        self.emit("progressInit", ("Collection", 100, False))
        self.collection_id = None

        try:
            # Prepare data collection
            self.open_detector_cover()
            self.open_safety_shutter()
            self.open_fast_shutter()

            # Store information in LIMS
            self.current_dc_parameters["status"] = "Running"
            self.current_dc_parameters["collection_start_time"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            logging.getLogger("HWR").info(
                "Collection parameters: %s", str(self.current_dc_parameters)
            )

            log.info("Collection: Storing data collection in LIMS")
            self.store_data_collection_in_lims()

            log.info("Collection: Getting sample info from parameters")
            self.get_sample_info()

            log.info("Collection: Storing sample info in LIMS")
            self.store_sample_info_in_lims()

            if all(
                item is None for item in self.current_dc_parameters["motors"].values()
            ):
                current_diffractometer_position = (
                    HWR.beamline.diffractometer.get_positions()
                )
                for motor in self.current_dc_parameters["motors"].keys():
                    self.current_dc_parameters["motors"][
                        motor
                    ] = current_diffractometer_position.get(motor)

            # Move to the centered position and take crystal snapshots
            log.info("Collection: Moving to centred position")
            self.move_to_centered_position()
            self.take_crystal_snapshots()
            self.move_to_centered_position()

            self.emit("progressStep", 2)
            # Set data collection parameters
            if "transmission" in self.current_dc_parameters:
                log.info(
                    "Collection: Setting transmission to %.2f",
                    self.current_dc_parameters["transmission"],
                )
                self.set_transmission(self.current_dc_parameters["transmission"])

            if "wavelength" in self.current_dc_parameters:
                log.info(
                    "Collection: Setting wavelength to %.4f",
                    self.current_dc_parameters["wavelength"],
                )
                self.set_wavelength(self.current_dc_parameters["wavelength"])

            elif "energy" in self.current_dc_parameters:
                log.info(
                    "Collection: Setting energy to %.4f",
                    self.current_dc_parameters["energy"],
                )
                self.set_energy(self.current_dc_parameters["energy"])

            dd = self.current_dc_parameters.get("resolution")
            if dd and dd.get("upper"):
                resolution = dd["upper"]
                log.info("Collection: Setting resolution to %.3f", resolution)
                self.set_resolution(resolution)

            elif "detector_distance" in self.current_dc_parameters:
                log.info(
                    "Collection: Moving detector to %.2f",
                    self.current_dc_parameters["detector_distance"],
                )
                self.move_detector(self.current_dc_parameters["detector_distance"])

            self.data_collection_hook()

            log.info("Collection: Updating data collection in LIMS")
            self.update_data_collection_in_lims()

        except RuntimeError as e:
            failed_msg = "Data collection failed!\n%s" % str(e)
            self.collection_failed(failed_msg)
        else:
            self.collection_finished()
        finally:
            self.data_collection_cleanup()

    def data_collection_hook(self):
        """Handles site-specific data collection processes."""
        dc_pars = self.current_dc_parameters
        collection_type = dc_pars["experiment_type"]

        self.log.debug(
            "======================= P11Collect. DATA COLLECTION HOOK =========================================="
        )
        self.log.debug(str(collection_type))
        self.log.debug(str(self.current_dc_parameters))

        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        file_info = self.current_dc_parameters["fileinfo"]
        osc_pars["kappa"] = 0
        osc_pars["kappa_phi"] = 0

        start_angle = osc_pars["start"]
        img_range = osc_pars["range"]
        nframes = osc_pars["number_of_images"]
        self.latest_frames = nframes
        stop_angle = start_angle + img_range * nframes

        img_range = osc_pars["range"]
        exp_time = osc_pars["exposure_time"]
        self.acq_speed = img_range / exp_time

        self.total_angle_range = abs(stop_angle - start_angle)

        if not self.diffractometer_prepare_collection():
            raise RuntimeError("Cannot prepare diffractometer for collection")

        self.emit("progressStep", 5)

        try:
            self.log.debug("############# #COLLECT# Opening detector cover")
            HWR.beamline.diffractometer.detector_cover_open(wait=True)
            self.log.debug(
                "############ #COLLECT# detector cover is now open. Wait 2 more seconds"
            )
            time.sleep(2.0)  # wait extra time to allow det cover to be opened.

            basepath = file_info["directory"]
            prefix = file_info["prefix"]
            runno = file_info["run_number"]

            self.log.debug("#COLLECT# Programming detector for data collection")
            if collection_type == "Characterization":

                # Prepares metadata taken from current osc parameters.
                self.prepare_characterization()
                self.log.info(
                    "Collection: Creating directories for raw images and processing files EDNA and MOSFLM"
                )
                self.create_characterisation_directories()
                # Filepath for the presented data to work
                filepath = os.path.join(
                    basepath,
                    prefix,
                    "screening_"
                    + str(runno).zfill(3)
                    + "/"
                    + "%s_%d" % (prefix, runno),
                )


                self.log.debug(
                    "======= CURRENT FILEPATH: "
                    + str(filepath)
                    + "======================================="
                )
                self.latest_h5_filename = "%s_master.h5" % filepath
                self.log.debug(
                    "======= LATEST H5 FILENAME FILEPATH: "
                    + str(self.latest_h5_filename)
                    + "======================================="
                )

                self.log.debug(
                    "======= CURRENT FILEPATH: "
                    + str(filepath)
                    + "======================================="
                )
                self.latest_h5_filename = "%s_master.h5" % filepath
                self.log.debug(
                    "======= LATEST H5 FILENAME FILEPATH: "
                    + str(self.latest_h5_filename)
                    + "======================================="
                )

                angle_inc = 90.0
                HWR.beamline.detector.prepare_characterisation(
                    exp_time, nframes, angle_inc, filepath
                )

            else:
                # Prepares metadata taken from current osc parameters.
                self.prepare_std_collection(start_angle, img_range)
                self.log.info(
                    "Collection: Creating directories for raw images and processing files"
                )
                self.create_file_directories()

                filepath = os.path.join(
                    basepath,
                    prefix,
                    "rotational_"
                    + str(runno).zfill(3)
                    + "/"
                    + "%s_%d" % (prefix, runno),
                )

                self.log.debug(
                    "======= CURRENT FILEPATH: "
                    + str(filepath)
                    + "======================================="
                )
                self.latest_h5_filename = "%s_master.h5" % filepath
                self.log.debug(
                    "======= LATEST H5 FILENAME FILEPATH: "
                    + str(self.latest_h5_filename)
                    + "======================================="
                )

                HWR.beamline.detector.prepare_std_collection(
                    exp_time, nframes, filepath
                )

            self.log.debug("#COLLECT# Starting detector")

            # Check whether the live view monitoring is on. Restart if needed.
            process_name = os.getenv("MXCUBE_LIVEVIEW_NAME")
            command = [os.getenv("MXCUBE_LIVEVIEW")]
            if self.is_process_running(process_name) and self.is_process_running(
                "adxv"
            ):
                self.log.debug(f"{process_name} is already running.")
            else:
                os.system(f"killall -9 {process_name}")
                self.log.debug(f"{process_name} is not running. Starting...")
                self.start_process(command)

            if collection_type == "Characterization":
                self.log.debug("STARTING CHARACTERISATION")
                self.collect_characterisation(
                    start_angle, img_range, nframes, angle_inc, exp_time
                )

                # Move to 0 with default speed (fast)
                HWR.beamline.diffractometer.set_omega_velocity(self.default_speed)
                time.sleep(0.1)
                HWR.beamline.diffractometer.move_omega(0)

                # Adding H5 info for characterization
                start_angles_collected = []
                for nf in range(nframes):
                    start_angles_collected.append(start_angle + nf * angle_inc)
                self.add_h5_info_characterisation(
                    self.latest_h5_filename, start_angles_collected, img_range
                )

                latest_image = HWR.beamline.detector.get_eiger_name_pattern()
                latest_local_path = os.path.dirname(f"/gpfs{latest_image}_master.h5")
                latest_local_name = f"/gpfs{latest_image}_master.h5".split("/")[-1]
                self.write_info_txt(
                    latest_local_path,
                    latest_local_name,
                    start_angle,
                    nframes,
                    img_range,
                    angle_inc,
                    exp_time,
                    "screening",
                )

            else:
                self.log.debug("STARTING STANDARD COLLECTION")
                duration = self.total_angle_range / self.acq_speed
                start_time = time.time()

                latest_image = HWR.beamline.detector.get_eiger_name_pattern()
                latest_local_path = os.path.dirname(f"/gpfs{latest_image}_master.h5")
                latest_local_name = f"/gpfs{latest_image}_master.h5".split("/")[-1]

                # Start the progress emitter in a separate greenlet
                gevent.spawn(self.progress_emitter, start_time, duration)

                HWR.beamline.diffractometer.wait_omega()

                # Arm the detector here. For characterization it is a bit different.
                HWR.beamline.detector.start_acquisition()
                self.collect_std_collection(start_angle, stop_angle)

                # Move to 0 with default speed (fast)
                HWR.beamline.diffractometer.set_omega_velocity(self.default_speed)
                time.sleep(0.1)
                HWR.beamline.diffractometer.move_omega(0)

                self.add_h5_info_standard_data_collection(self.latest_h5_filename)

                self.write_info_txt(
                    latest_local_path,
                    latest_local_name,
                    start_angle,
                    nframes,
                    img_range,
                    stop_angle - start_angle,
                    exp_time,
                    "regular",
                )

        except RuntimeError:
            self.log.error(traceback.format_exc())
        finally:
            self.acquisition_cleanup()

        latest_image = HWR.beamline.detector.get_eiger_name_pattern()
        latest_image = f"/gpfs{latest_image}_master.h5"
        self.adxv_notify(latest_image)

    def progress_emitter(self, start_time, duration):
        """Emits progress steps during data collection.

        Args:
            start_time (float): Start time of the data collection.
            duration (float): Estimated duration of the data collection.
        """
        while True:
            elapsed_time = time.time() - start_time
            progress = (elapsed_time / duration) * 100

            if progress >= 100:
                progress = 98
                self.emit("progressStep", progress)
                break
            self.emit("progressStep", progress)
            gevent.sleep(1)  # Non-blocking sleep

    def add_h5_info_standard_data_collection(self, imagepath):
        """Adds metadata to the HDF5 file for a standard data collection.

        Args:
            imagepath (str): Path to the HDF5 file.
        """
        time.sleep(1)
        self.log.debug("adding h5 info for standard data collection")
        try:
            f = h5py.File(imagepath, "r+")
            # source and instrument
            g = f.create_group("entry/source")
            g.attrs["NX_class"] = np.array("NXsource", dtype="S")
            g.create_dataset("name", data=np.array("PETRA III, DESY", dtype="S"))
            g = f.get("entry/instrument")
            g.create_dataset("name", data=np.array("P11", dtype="S"))
            # attenuator
            g = f.create_group("entry/instrument/attenuator")
            g.attrs["NX_class"] = np.array("NXattenuator", dtype="S")
            ds = g.create_dataset(
                "thickness", dtype="f8", data=float(self.get_filter_thickness())
            )
            ds.attrs["units"] = np.array("m", dtype="S")
            ds = g.create_dataset("type", data=np.array("Aluminum", dtype="S"))
            ds = g.create_dataset(
                "attenuator_transmission",
                dtype="f8",
                data=float(self.get_filter_transmission()),
            )

            # Keep it here as it is not clear if it is needed.
            # It was used in CC to fix the issue with the data processing

            # #fix rotation axis and detector orientation
            # ds = f.get(u"entry/sample/transformations/omega")
            # ds.attrs[u"vector"] = [1., 0., 0.]
            # ds = f.get(u"entry/instrument/detector/module/fast_pixel_direction")
            # ds.attrs[u"vector"] = [1., 0., 0.]
            # ds = f.get(u"entry/instrument/detector/module/slow_pixel_direction")
            # ds.attrs[u"vector"] = [0., 1., 0.]
            # delete phi angle info to avoid confusion
            nodes = [
                "entry/sample/goniometer/phi",
                "entry/sample/goniometer/phi_end",
                "entry/sample/goniometer/phi_range_average",
                "entry/sample/goniometer/phi_range_total",
            ]
            for node in nodes:
                if node in f:
                    del f[node]
            f.close()
        except RuntimeWarning:
            self.log.debug("writing header to H5 FAILED!")
    def add_h5_info_characterisation(
        self, imagepath, start_angles_collected, degreesperframe
    ):
        """Adds metadata to the HDF5 file for characterization data collection.

        Args:
            imagepath (str): Path to the HDF5 file.
            start_angles_collected (list): List of angles at which images were collected.
            degreesperframe (float): Number of degrees per frame collected.
        """
        time.sleep(1)
        self.log.debug("adding h5 info for characterization")
        try:
            f = h5py.File(imagepath, "r+")
            # source and instrument
            g = f.create_group("entry/source")
            g.attrs["NX_class"] = np.array("NXsource", dtype="S")
            g.create_dataset("name", data=np.array("PETRA III, DESY", dtype="S"))
            g = f.get("entry/instrument")
            g.create_dataset("name", data=np.array("P11", dtype="S"))
            # attenuator
            g = f.create_group("entry/instrument/attenuator")
            g.attrs["NX_class"] = np.array("NXattenuator", dtype="S")
            ds = g.create_dataset(
                "thickness", dtype="f8", data=float(self.get_filter_thickness())
            )
            ds.attrs["units"] = np.array("m", dtype="S")
            ds = g.create_dataset("type", data=np.array("Aluminum", dtype="S"))
            ds = g.create_dataset(
                "attenuator_transmission",
                dtype="f8",
                data=float(self.get_filter_transmission()),
            )
            # delete existing angle info
            nodes = [
                "entry/sample/goniometer/omega",
                "entry/sample/goniometer/omega_end",
                "entry/sample/goniometer/omega_range_average",
                "entry/sample/goniometer/omega_range_total",
                "entry/sample/goniometer/phi",
                "entry/sample/goniometer/phi_end",
                "entry/sample/goniometer/phi_range_average",
                "entry/sample/goniometer/phi_range_total",
                "entry/sample/transformations/omega",
                "entry/sample/transformations/omega_end",
                "entry/sample/transformations/omega_range_average",
                "entry/sample/transformations/omega_range_total",
            ]
            for node in nodes:
                if node in f:
                    del f[node]

            angles = []
            angles_end = []
            for angle in start_angles_collected:
                angles.append(float(angle))
                angles_end.append(float(angle + degreesperframe))
            g = f.get("entry/sample/goniometer")
            o = g.create_dataset("omega", dtype="f8", data=angles)
            o.attrs["vector"] = [1.0, 0.0, 0.0]
            g.create_dataset("omega_end", dtype="f8", data=angles_end)
            g.create_dataset(
                "omega_range_average", dtype="f8", data=float(degreesperframe)
            )
            g = f.get("entry/sample/transformations")
            o = g.create_dataset("omega", dtype="f8", data=angles)
            o.attrs["vector"] = [1.0, 0.0, 0.0]
            g.create_dataset("omega_end", dtype="f8", data=angles_end)
            g.create_dataset(
                "omega_range_average", dtype="f8", data=float(degreesperframe)
            )
            f.close()
        except RuntimeWarning:
            self.log.debug("writing header to H5 characterization FAILED!")

    def write_info_txt(
        self,
        path,
        name,
        startangle,
        frames,
        degreesperframe,
        imageinterval,
        exposuretime,
        run_type,
    ):
        """Writes info about the data collection into a text file.

        Args:
            path (str): Directory path where the info file will be saved.
            name (str): Name of the run.
            startangle (float): Starting angle of the collection.
            frames (int): Number of frames collected.
            degreesperframe (float): Degrees per frame.
            imageinterval (float): Interval between images.
            exposuretime (float): Exposure time in milliseconds.
            run_type (str): Type of run (e.g., 'regular' or 'screening').
        """
        if run_type == "regular":

            INFO_TXT = (
                "run type:            {run_type:s}\n"
                + "run name:            {name:s}\n"
                + "start angle:         {startangle:.2f}deg\n"
                + "frames:              {frames:d}\n"
                + "degrees/frame:       {degreesperframe:.2f}deg\n"
                + "exposure time:       {exposuretime:.3f}ms\n"
                + "energy:              {energy:.3f}keV\n"
                + "wavelength:          {wavelength:.3f}A\n"
                + "detector distance:   {detectordistance:.2f}mm\n"
                + "resolution:          {resolution:.2f}A\n"
                + "aperture:            {pinholeDiameter:d}um\n"
                + "focus:               {focus:s}\n"
                + "filter transmission: {filterTransmission:.3f}%\n"
                + "filter thickness:    {filterThickness:d}um\n"
                + "ring current:        {beamCurrent:.3f}mA\n"
                + "\n"
                + "For exact flux reading, please consult the staff."
            )

            energy = HWR.beamline.energy.get_value()
            wavelength = 12.3984 / (energy)  # in Angstrom
            resolution = HWR.beamline.resolution.get_value()
            detectordistance = HWR.beamline.detector.get_eiger_detector_distance()
            transmission = HWR.beamline.transmission.get_value()
            filter_thickness = self.get_filter_thickness_in_mm()
            pinhole_diameter = HWR.beamline.beam.get_pinhole_size()
            focus = HWR.beamline.beam.get_beam_focus_label()
            current = HWR.beamline.machine_info.get_current()

            output = INFO_TXT.format(
                run_type=run_type,
                name=name,
                startangle=startangle,
                frames=frames,
                degreesperframe=degreesperframe,
                exposuretime=exposuretime * 1000,
                energy=energy,
                wavelength=wavelength,
                detectordistance=detectordistance,
                resolution=resolution,
                pinholeDiameter=int(pinhole_diameter),
                focus=str(focus),
                filterTransmission=int(transmission),
                filterThickness=int(filter_thickness),
                beamCurrent=float(current),
            )

            f = open(path + "/info.txt", "w")
            f.write(output)
            f.close()

        if run_type == "screening":

            INFO_TXT = (
                "run type:            {run_type:s}\n"
                + "run name:            {name:s}\n"
                + "start angle:         {startangle:.2f}deg\n"
                + "frames:              {frames:d}\n"
                + "degrees/frame:       {degreesperframe:.2f}deg\n"
                + "exposure time:       {exposuretime:.3f}ms\n"
                + "energy:              {energy:.3f}keV\n"
                + "wavelength:          {wavelength:.3f}A\n"
                + "detector distance:   {detectordistance:.2f}mm\n"
                + "resolution:          {resolution:.2f}A\n"
                + "aperture:            {pinholeDiameter:d}um\n"
                + "focus:               {focus:s}\n"
                + "filter transmission: {filterTransmission:.3f}%\n"
                + "filter thickness:    {filterThickness:d}um\n"
                + "ring current:        {beamCurrent:.3f}mA\n"
                + "\n"
                + "For exact flux reading, please consult the staff."
            )

            energy = HWR.beamline.energy.get_value()
            wavelength = 12.3984 / (energy)  # in Angstrom
            resolution = HWR.beamline.resolution.get_value()
            detectordistance = HWR.beamline.detector.get_eiger_detector_distance()
            transmission = HWR.beamline.transmission.get_value()
            filter_thickness = self.get_filter_thickness_in_mm()
            pinhole_diameter = HWR.beamline.beam.get_pinhole_size()
            focus = HWR.beamline.beam.get_beam_focus_label()
            current = HWR.beamline.machine_info.get_current()

            output = INFO_TXT.format(
                run_type=run_type,
                name=name,
                startangle=startangle,
                frames=frames,
                degreesperframe=degreesperframe,
                exposuretime=exposuretime * 1000,
                energy=energy,
                wavelength=wavelength,
                detectordistance=detectordistance,
                resolution=resolution,
                pinholeDiameter=int(pinhole_diameter),
                focus=str(focus),
                filterTransmission=int(transmission),
                filterThickness=int(filter_thickness),
                beamCurrent=float(current),
            )

            f = open(path + "/info.txt", "w")
            f.write(output)
            f.close()

    def prepare_characterization(self):
        """Prepares for characterization data collection by setting the start angle and angle increment for the detector."""
        self.log.debug("Preparing for characterization data collection.")

        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        start_angle = osc_pars["start"]
        HWR.beamline.detector.set_eiger_start_angle(start_angle)

        img_range = osc_pars["range"]
        HWR.beamline.detector.set_eiger_angle_increment(img_range)

    def collect_characterisation(
        self, start_angle, img_range, nimages, angle_inc, exp_time
    ):
        """Collects a series of images at different angles for characterization.

        Args:
            start_angle (float): Starting angle for the characterization acquisition.
            img_range (float): Range of angles over which a single image is collected.
            nimages (int): Number of images to be collected during the characterization process.
            angle_inc (float): Increment in angle between each image in the collection.
            exp_time (float): Exposure time for each image.
        """
        self.log.debug(
            "#COLLECT# Running OMEGA through the characterization acquisition"
        )

        start_angle = int(start_angle)

        for img_no in range(nimages):
            self.log.debug("collecting image %s" % img_no)
            start_at = start_angle + angle_inc * img_no
            stop_angle = start_at + img_range * 1.0

            self.log.debug("collecting image %s, angle %f" % (img_no, start_at))

            #[WIP]
            #NB! Another attemt to fix the misfires. 
            #Keep comments here until finished
            #Here is the previous implementation:
            #self.collect_std_collection(start_at, stop_angle)
            
            #Here is sligthly modified standard data collection routine
            #Adjust the angle since each time we are starting with 90 degrees offset.
            start_pos = start_at - self.turnback_time * self.acq_speed
            stop_pos = stop_angle + self.turnback_time * self.acq_speed

            self.log.debug("#COLLECT# Running OMEGA through the std acquisition")
            HWR.beamline.diffractometer.wait_omega_on()
            HWR.beamline.diffractometer.set_omega_velocity(self.default_speed)
            time.sleep(1)
            HWR.beamline.diffractometer.move_omega(start_pos)
            time.sleep(1)
            HWR.beamline.diffractometer.wait_omega_on()
            time.sleep(1)
            # NB! angles reversed could work???
            HWR.beamline.diffractometer.set_pso_control_arm(start_angle, stop_angle)
            time.sleep(3)
            HWR.beamline.diffractometer.set_omega_velocity(self.acq_speed)
            time.sleep(1)

            #Arm the detector only once in the beginning. Set to wait 4 triggers. 
            if img_no == 0:
                HWR.beamline.detector.start_acquisition()
                time.sleep(3)
            
            HWR.beamline.diffractometer.move_omega(stop_pos)

            self.emit("progressStep", int(120 / (nimages) * (img_no + 1)))

    def prepare_std_collection(self, start_angle, img_range):
        """Prepares a standard collection by setting the start angle and angle increment in the detector's header.

        Args:
            start_angle (float): Starting angle for the standard collection sequence.
            img_range (float): Angle increment for each frame.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        start_angle = osc_pars["start"]
        HWR.beamline.detector.set_eiger_start_angle(start_angle)

        img_range = osc_pars["range"]
        HWR.beamline.detector.set_eiger_angle_increment(img_range)

    def collect_std_collection(self, start_angle, stop_angle):
        """Performs the standard data collection by moving the omega motor from start to stop angle.

        Args:
            start_angle (float): Starting angle for the collection.
            stop_angle (float): Stop angle for the collection.
        """
        start_pos = start_angle - self.turnback_time * self.acq_speed
        stop_pos = stop_angle + self.turnback_time * self.acq_speed

        self.log.debug("#COLLECT# Running OMEGA through the std acquisition")
        HWR.beamline.diffractometer.wait_omega_on()
        HWR.beamline.diffractometer.set_omega_velocity(self.default_speed)
        time.sleep(1)
        HWR.beamline.diffractometer.move_omega(start_pos)
        time.sleep(1)
        HWR.beamline.diffractometer.wait_omega_on()
        time.sleep(1)
        HWR.beamline.diffractometer.set_pso_control_arm(start_angle, stop_angle)
        time.sleep(3)
        HWR.beamline.diffractometer.set_omega_velocity(self.acq_speed)
        time.sleep(1)
        HWR.beamline.diffractometer.move_omega(stop_pos)

    
    def adxv_notify(self, image_filename, image_num=1):
        """Sends a notification to an ADXV to load an image file and display a specific slab.

        Args:
            image_filename (str): Filename of the image to be loaded.
            image_num (int, optional): Image number to load in ADXV. Defaults to 1.
        """
        logging.getLogger("HWR").info(f"ADXV notify {image_filename}")
        logging.getLogger("HWR").info(f"ADXV notify {image_num}")
        adxv_host = "localhost"
        adxv_port = 8100

        try:
            adxv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            adxv_socket.connect((adxv_host, adxv_port))
            adxv_socket.sendall(
                f"load_image {image_filename}\n slab {image_num}\n".encode()
            )
            adxv_socket.close()
        except RuntimeWarning:
            logging.getLogger("HWR").exception("")
        else:
            pass

    def is_process_running(self, process_name):
        """Checks if a process is running by its name.

        Args:
            process_name (str): Name of the process to check.

        Returns:
            bool: True if the process is running, False otherwise.
        """
        for proc in psutil.process_iter():
            if proc.name() == process_name:
                return True
        return False

    def start_process(self, command):
        """Starts a process with the specified command.

        Args:
            command (list): List of command arguments to start the process.
        """
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )

    def acquisition_cleanup(self):
        """Performs cleanup after data acquisition, including stopping the detector and resetting motor velocities."""
        try:
            HWR.beamline.detector.stop_acquisition()
            HWR.beamline.diffractometer.wait_omega()
            HWR.beamline.diffractometer.set_omega_velocity(self.default_speed)
            self.log.debug("#COLLECT# Closing detector cover")
            HWR.beamline.diffractometer.detector_cover_close(wait=True)

            HWR.beamline.diffractometer.stop_motion()

        except RuntimeError:
            self.log.error(traceback.format_exc())

    def get_or_create_group(self, parent_group, group_name):
        """Gets or creates a group within a parent group.

        Args:
            parent_group (h5py.Group): The parent group where the new group will be created.
            group_name (str): The name of the group to get or create.

        Returns:
            h5py.Group: The group object.
        """
        if group_name in parent_group:
            return parent_group[group_name]
        else:
            return parent_group.create_group(group_name)

    def create_or_get_dataset(self, group, dataset_name, dataset_data):
        """Creates or retrieves a dataset within a group.

        Args:
            group (h5py.Group): The group where the dataset will be created or retrieved.
            dataset_name (str): The name of the dataset.
            dataset_data: The data to be stored in the dataset.
        """
        if dataset_name in group:
            dataset = group[dataset_name]
        else:
            dataset = group.create_dataset(dataset_name, data=dataset_data)

    def get_filter_thickness(self):
        """Calculates the total thickness of three filters.

        Returns:
            float: The total thickness of the filters in meters. If the filter server is not available, it returns -1.
        """
        if self.filter_server:
            thick1 = self.filter_server.Filter1Thickness
            thick2 = self.filter_server.Filter2Thickness
            thick3 = self.filter_server.Filter3Thickness

            thickness = int(thick1) + int(thick2) + int(thick3)
            return float(thickness) / 1_000_000
        else:
            return -1

    def get_filter_thickness_in_mm(self):
        """Calculates the total thickness of three filters in millimeters.

        Returns:
            int: The total thickness of the filters in millimeters. If the filter server is not available, it returns -1.
        """
        if self.filter_server:
            thick1 = self.filter_server.Filter1Thickness
            thick2 = self.filter_server.Filter2Thickness
            thick3 = self.filter_server.Filter3Thickness

            thickness = int(thick1) + int(thick2) + int(thick3)

            return int(thickness)
        else:
            return -1

    def get_filter_transmission(self):
        """Gets the current transmission value from the filter server.

        Returns:
            float: The current transmission value. If the filter server is not available, it returns -1.
        """
        if self.filter_server:
            return self.filter_server.CurrentTransmission
        else:
            return -1

    def xdsapp_maxwell(self):
        """Starts XDSAPP auto-processing on the Maxwell cluster."""
        
        if HWR.beamline.session.get_beamtime_metadata() != None:

            self.log.debug("==== XDSAPP AUTOPROCESSING IS STARTED ==========")

            resolution = self.get_resolution()

            image_dir_local, filename = os.path.split(self.latest_h5_filename)

            image_dir = image_dir_local.replace(
                "/gpfs/current", HWR.beamline.session.get_beamtime_metadata()[2]
            )
            process_dir = image_dir.replace("/raw/", "/processed/")
            process_dir_local = image_dir_local.replace("/raw/", "/processed/")
            xdsapp_path = os.path.join(process_dir, "xdsapp")
            xdsapp_path_local = os.path.join(process_dir_local, "xdsapp")
            self.log.debug('============XDSAPP======== xdsapp_path="%s"' % xdsapp_path)
            self.log.debug(
                '============XDSAPP======== xdsapp_path_local="%s"' % xdsapp_path_local
            )

            try:
                self.mkdir_with_mode(xdsapp_path_local, mode=0o777)
                self.log.debug("=========== XDSAPP ============ XDSAPP directory created")

            except OSError:
                self.log.debug(sys.exc_info())
                self.log.debug("Cannot create XDSAPP directory")

            base_process_dir = self.base_dir(process_dir_local, "processed")
            datasets_file = os.path.join(base_process_dir, "datasets.txt")

            try:
                open(datasets_file, "a", encoding="utf-8").write(
                    xdsapp_path_local.split("/gpfs/current/processed/")[1] + "\n"
                )
            except RuntimeError as err_msg:
                self.log.debug("Cannot write to datasets.txt")
                self.log.debug(sys.exc_info())

            ssh = HWR.beamline.session.get_ssh_command()
            sbatch = HWR.beamline.session.get_sbatch_command(
                jobname_prefix="xdsapp",
                logfile_path=xdsapp_path.replace(
                    HWR.beamline.session.get_beamtime_metadata()[2], "/beamline/p11/current"
                )
                + "/xdsapp.log",
            )

            cmd = (
                "/asap3/petra3/gpfs/common/p11/processing/xdsapp_sbatch.sh "
                + "{imagepath:s} {processpath:s} {res:f}"
            ).format(
                imagepath=image_dir + "/" + filename,
                processpath=xdsapp_path.replace(
                    HWR.beamline.session.get_beamtime_metadata()[2], "/beamline/p11/current"
                ),
                res=resolution,
            )

            os.system(
                '{ssh:s} "{sbatch:s} --wrap \\"{cmd:s}\\""'.format(
                    ssh=ssh, sbatch=sbatch, cmd=cmd
                )
            )
        else:
            self.log.debug("Beamtime metadata is not found. No online resouces available. Autoprocessing on the cluster is not available.")

    def autoproc_maxwell(self):
        """Starts AutoProc auto-processing on the Maxwell cluster."""
            
        if HWR.beamline.session.get_beamtime_metadata() != None:

            self.log.debug("==== AUTOPROC AUTOPROCESSING IS STARTED ==========")

            resolution = self.get_resolution()

            image_dir_local, filename = os.path.split(self.latest_h5_filename)

            image_dir = image_dir_local.replace(
                "/gpfs/current", HWR.beamline.session.get_beamtime_metadata()[2]
            )
            process_dir = image_dir.replace("/raw/", "/processed/")
            process_dir_local = image_dir_local.replace("/raw/", "/processed/")
            autoproc_path = os.path.join(process_dir, "autoproc")
            autoproc_path_local = os.path.join(process_dir_local, "autoproc")
            self.log.debug(
                '============AUTOPROC======== autoproc_path="%s"' % autoproc_path
            )
            self.log.debug(
                '============AUTOPROC======== autoproc_path_local="%s"'
                % autoproc_path_local
            )

            try:
                self.mkdir_with_mode(autoproc_path_local, mode=0o777)
                self.log.debug(
                    "=========== AUTOPROC ============ autoproc directory created"
                )

            except OSError:
                self.log.debug(sys.exc_info())
                self.log.debug("Cannot create AUTOPROC directory")

            base_process_dir = self.base_dir(process_dir_local, "processed")
            datasets_file = os.path.join(base_process_dir, "datasets.txt")

            try:
                open(datasets_file, "a", encoding="utf-8").write(
                    autoproc_path_local.split("/gpfs/current/processed/")[1] + "\n"
                )
            except RuntimeError as err_msg:
                self.log.debug("Cannot write to datasets.txt")
                self.log.debug(sys.exc_info())

            ssh = HWR.beamline.session.get_ssh_command()
            sbatch = HWR.beamline.session.get_sbatch_command(
                jobname_prefix="autoproc",
                logfile_path=autoproc_path.replace(
                    HWR.beamline.session.get_beamtime_metadata()[2], "/beamline/p11/current"
                )
                + "/autoproc.log",
            )

            cmd = (
                "/asap3/petra3/gpfs/common/p11/processing/autoproc_sbatch.sh "
                + "{imagepath:s} {processpath:s}"
            ).format(
                imagepath=image_dir + "/" + filename,
                processpath=autoproc_path.replace(
                    HWR.beamline.session.get_beamtime_metadata()[2], "/beamline/p11/current"
                )
                + "/processing",
            )

            os.system(
                '{ssh:s} "{sbatch:s} --wrap \\"{cmd:s}\\""'.format(
                    ssh=ssh, sbatch=sbatch, cmd=cmd
                )
            )
        else:
            self.log.debug("Beamtime metadata is not found. No online resouces available. Autoprocessing on the cluster is not available.")

    def trigger_auto_processing(self, process_event=None, frame_number=None):
        """Triggers auto processing based on the experiment type.

        Args:
            process_event: Optional event that triggered the auto processing.
            frame_number (int, optional): Number of frames to process.
        """
        self.log.debug("Triggering auto processing")
        collection_type = self.current_dc_parameters["experiment_type"]
        self.log.debug(
            "=============== Supported experiment types: ===========\n"
            + str(self.current_dc_parameters["experiment_type"])
        )

        self.xdsapp_maxwell()
        self.autoproc_maxwell()

    def diffractometer_prepare_collection(self):
        """Prepares the diffractometer for data collection.

        Returns:
            bool: True if the diffractometer is in collect phase, False otherwise.
        """
        self.log.debug("#COLLECT# preparing collection ")
        if not HWR.beamline.diffractometer.is_collect_phase():
            self.log.debug("#COLLECT# going to collect phase")
            HWR.beamline.diffractometer.goto_collect_phase(wait=True)

        self.log.debug(
            "#COLLECT# now in collect phase: %s"
            % HWR.beamline.diffractometer.is_collect_phase()
        )

        return HWR.beamline.diffractometer.is_collect_phase()

    def get_relative_path(self, path1, path2):
        """Returns the relative path from path1 to path2.

        Args:
            path1 (str): First path.
            path2 (str): Second path.

        Returns:
            str: The relative path between path1 and path2.
        """
        path_1 = path1.split(os.path.sep)
        path_2 = path2.split(os.path.sep)

        for i, v__ in enumerate(path_2):
            if path_1[i] != v__:
                break

            parts = [".."] * (len(path_2) - i)
            parts.extend(path_1[i:])

        return os.path.join(*parts)

    def base_dir(self, path, what):
        """Returns the base directory path that contains the specified "what" directory or file.

        Args:
            path (str): The path to a file or directory.
            what (str): The directory or file name to search for.

        Returns:
            str: The base directory containing the "what".
        """
        what = what.lstrip(os.path.sep)

        if path.startswith(os.path.sep):
            start_sep = os.path.sep
        else:
            start_sep = ""

        path_ = path.split(os.path.sep)
        for i, v__ in enumerate(path_):
            if path_[i] == what:
                break

        return start_sep + os.path.join(*path_[: i + 1])

    def mkdir_with_mode(self, directory, mode):
        """Creates a directory with the specified mode.

        Args:
            directory (str): Path of the directory to create.
            mode (int): Mode (permissions) to set for the directory.
        """
        if not os.path.isdir(directory):
            oldmask = os.umask(000)
            os.makedirs(directory, mode=mode)
            os.umask(oldmask)

            self.log.debug("local directory created")

    def create_directories(self, *args):
        """Creates directories for raw files and processing files."""
        for directory in args:
            try:
                self.mkdir_with_mode(directory, mode=0o777)
            except os.error as err_:
                if err_.errno != errno.EEXIST:
                    raise

    def check_path(self, path=None, force=False):
        """Checks if a path is valid and accessible, and creates directories if needed.

        Args:
            path (str, optional): The path to check. Defaults to None.
            force (bool, optional): Whether to create the directories if they don't exist. Defaults to False.

        Returns:
            str or bool: The path if valid and accessible, or False if not.
        """
        path = str(path).replace("\\", "/")
        dirs = path.strip("/").split("/")
        path = ""
        for dir_ in dirs:
            if dir_.find("*") > -1 or dir_.find("?") > -1 or dir_.find("..") > -1:
                return False
            path += "/" + dir_
            if not os.access(path, os.F_OK):
                if force:
                    try:
                        os.mkdir(path, mode=0o777)
                    except RuntimeError:
                        self.log.debug("mkdir failed:", str(sys.exc_info()))
                        return False
                else:
                    self.log.debug("dir not found:", str(sys.exc_info()))
                    return False
        if not os.access(path, os.W_OK):
            self.log.debug("dir not writable:", str(sys.exc_info()))
            return False
        return path

    def create_characterisation_directories(self):
        """Creates directories for raw files and processing files for EDNA and MOSFLM."""
        self.create_directories(
            self.current_dc_parameters["fileinfo"]["directory"],
            self.current_dc_parameters["fileinfo"]["process_directory"],
        )

        collection_type = HWR.beamline.collect.current_dc_parameters["experiment_type"]
        self.log.debug("PREPARING FOLDERS FOR COLLECTION TYPE", collection_type)

        xds_directory, auto_directory = self.prepare_input_files()
        xds_directory = xds_directory.replace("/rotational_", "/screening_").replace(
            "/xdsapp", "/edna"
        )
        auto_directory = auto_directory.replace("/rotational_", "/screening_").replace(
            "/xdsapp", "/edna"
        )
        try:
            self.create_directories(xds_directory, auto_directory)
            os.system("chmod -R 777 %s %s" % (xds_directory, auto_directory))
        except Exception:
            logging.exception("Could not create processing file directory")
            return
        if xds_directory:
            self.current_dc_parameters["xds_dir"] = xds_directory
        if auto_directory:
            self.current_dc_parameters["auto_dir"] = auto_directory

    def create_file_directories(self):
        """Creates directories for raw files and processing files."""
        self.create_directories(
            self.current_dc_parameters["fileinfo"]["directory"],
            self.current_dc_parameters["fileinfo"]["process_directory"],
        )

        xds_directory, auto_directory = self.prepare_input_files()
        try:
            self.create_directories(xds_directory, auto_directory)
            os.system("chmod -R 777 %s %s" % (xds_directory, auto_directory))
        except Exception:
            logging.exception("Could not create processing file directory")
            return
        if xds_directory:
            self.current_dc_parameters["xds_dir"] = xds_directory
        if auto_directory:
            self.current_dc_parameters["auto_dir"] = auto_directory

    def prepare_input_files(self):
        """Prepares directories for processing input files.

        Returns:
            tuple: Paths for XDS and AutoProc directories.
        """
        logging.getLogger("user_level_log").info(
            "Creating XDS processing input file directories"
        )

        xds_input_file_dirname = (
            "%s" % (self.current_dc_parameters["fileinfo"]["prefix"],)
            + "/rotational_"
            + str(self.current_dc_parameters["fileinfo"]["run_number"]).zfill(3)
        )
        xds_directory = os.path.join(
            self.current_dc_parameters["fileinfo"]["directory"].replace(
                "/current/raw", "/current/processed"
            ),
            xds_input_file_dirname,
            "xdsapp",
        )

        auto_directory = xds_directory

        logging.getLogger("HWR").info(
            "[COLLECT] Processing input file directories: XDS: %s, AUTO: %s"
            % (xds_directory, auto_directory)
        )
        return xds_directory, auto_directory

    def take_crystal_snapshots(self):
        """Takes sample snapshots and saves them to disk."""
        if self.current_dc_parameters["take_snapshots"]:
            snapshot_directory = os.path.join(
                self.current_dc_parameters["fileinfo"]["directory"], "snapshot"
            )
            if not os.path.exists(snapshot_directory):
                try:
                    self.create_directories(snapshot_directory)
                except Exception:
                    logging.getLogger("HWR").exception(
                        "Collection: Error creating snapshot directory"
                    )

            number_of_snapshots = self.current_dc_parameters["take_snapshots"]
            logging.getLogger("user_level_log").info(
                "Collection: Taking %d sample snapshot(s)" % number_of_snapshots
            )
            if HWR.beamline.diffractometer.get_current_phase() != "Centring":
                logging.getLogger("user_level_log").info(
                    "Moving Diffractometer to CentringPhase"
                )
                HWR.beamline.diffractometer.goto_centring_phase(wait=True)
                self.move_to_centered_position()

            for snapshot_index in range(number_of_snapshots):
                snapshot_filename = os.path.join(
                    snapshot_directory,
                    "%s_%s_%s.snapshot.jpeg"
                    % (
                        self.current_dc_parameters["fileinfo"]["prefix"],
                        self.current_dc_parameters["fileinfo"]["run_number"],
                        (snapshot_index + 1),
                    ),
                )
                self.current_dc_parameters[
                    "xtalSnapshotFullPath%i" % (snapshot_index + 1)
                ] = snapshot_filename
                self._take_crystal_snapshot(snapshot_filename)
                time.sleep(1)  # needed, otherwise will get the same images
                if number_of_snapshots > 1:
                    HWR.beamline.diffractometer.move_omega_relative(90)
                    time.sleep(1)  # needed, otherwise will get the same images
