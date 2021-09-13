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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""LimaEigerDetector Class
Lima Tango Device Server implementation of the Dectris Eiger2 Detector.
"""
import os
import math
import logging
from gevent import Timeout, sleep

from mxcubecore.TaskUtils import task
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector


class LimaEigerDetector(AbstractDetector):
    """Control Eiger Detector using Lima Tango DS"""

    def __init__(self, name):
        super().__init__(name)
        self.binning_mode = 1

    def init(self):
        super().init()

        lima_device = self.get_property("lima_device")
        eiger_device = self.get_property("eiger_device")

        for channel_name in (
            "acq_status",
            "acq_trigger_mode",
            "acq_nb_sequences",
            "saving_mode",
            "acq_nb_frames",
            "acq_expo_time",
            "saving_directory",
            "saving_prefix",
            "saving_suffix",
            "saving_next_number",
            "saving_index_format",
            "saving_format",
            "saving_overwrite_policy",
            "last_image_saved",
            "saving_frame_per_file",
            "saving_managed_mode",
            "saving_common_header",
        ):
            self.add_channel(
                {"type": "tango", "name": channel_name, "tangoname": lima_device},
                channel_name,
            )

        for channel_name in ("photon_energy",):
            self.add_channel(
                {"type": "tango", "name": channel_name, "tangoname": eiger_device},
                channel_name,
            )

        self.add_command(
            {"type": "tango", "name": "prepare_acq", "tangoname": lima_device},
            "prepareAcq",
        )
        self.add_command(
            {"type": "tango", "name": "start_acq", "tangoname": lima_device}, "startAcq"
        )
        self.add_command(
            {"type": "tango", "name": "stop_acq", "tangoname": lima_device}, "stopAcq"
        )
        self.add_command(
            {"type": "tango", "name": "reset", "tangoname": lima_device}, "reset"
        )

        self.get_command_object("prepare_acq").init_device()
        self.get_command_object("prepare_acq").device.set_timeout_millis(5 * 60 * 1000)
        self.get_channel_object("photon_energy").init_device()
        self._emit_status()

    def has_shutterless(self):
        return True

    def wait_ready(self, timeout=30):
        """Wait the detector to be ready for a subsequent command
        Args:
            (float): timeout [s] - default 30s
                     timeout == 0: return at once and do not wait
                     timeout is None: wait forever.
        """
        acq_status_chan = self.get_channel_object("acq_status")
        with Timeout(timeout, RuntimeError("Detector not ready")):
            while acq_status_chan.get_value() != "Ready":
                sleep(1)

    def last_image_saved(self):
        """Get the last saved image number.
        Returns:
            (int): Las image saved number
        """
        return self.get_channel_object("last_image_saved").get_value() + 1

    def get_deadtime(self):
        """Get deadtime between each frame property
        Returns:
            (float): The deadtime [ms]
        """
        return float(self.get_property("deadtime"))

    def prepare_acquisition(
        self,
        take_dark,
        start,
        osc_range,
        exptime,
        npass,
        number_of_images,
        comment,
        mesh,
        mesh_num_lines,
    ):
        print(f"Unsed, but kept for completeness: take_dark {take_dark}, ")
        print(f"start {start}, npass {npass}, comment {comment}, ")
        print(f"mesh_num_lines {mesh_num_lines}\n")
        self.stop()
        self.wait_ready()
        beam_x, beam_y = self.get_beam_position()

        header_info = [
            "beam_center_x=%s" % (beam_x / 7.5000003562308848e-02),
            "beam_center_y=%s" % (beam_y / 7.5000003562308848e-02),
            "wavelength=%s" % HWR.beamline.energy.get_wavelength(),
            "detector_distance=%s"
            % (HWR.beamline.detector.distance.get_value() / 1000.0),
            "omega_start=%0.4f" % start,
            "omega_increment=%0.4f" % osc_range,
        ]
        self.get_channel_object("saving_common_header").set_value(header_info)

        if mesh:
            self.get_channel_object("acq_trigger_mode").set_value(
                "EXTERNAL_TRIGGER_MULTI"
            )
        elif osc_range < 1e-4:
            self.set_channel_value("acq_trigger_mode", "INTERNAL_TRIGGER")
        else:
            self.set_channel_value("acq_trigger_mode", "EXTERNAL_TRIGGER")

        self.get_channel_object("saving_frame_per_file").set_value(
            min(100, number_of_images)
        )

        # 'MANUAL', 'AUTO_FRAME', 'AUTO_SEQUENCE'
        self.get_channel_object("saving_mode").set_value("AUTO_FRAME")
        logging.info("Acq. nb frames = %d", number_of_images)
        self.get_channel_object("acq_nb_frames").set_value(number_of_images)
        self.get_channel_object("acq_expo_time").set_value(exptime)
        # 'ABORT', 'OVERWRITE', 'APPEND'
        self.get_channel_object("saving_overwrite_policy").set_value("OVERWRITE")
        # 'SOFTWARE', 'HARDWARE'
        self.get_channel_object("saving_managed_mode").set_value("HARDWARE")

    def set_energy_threshold(self, energy):
        """Set the energy threshold. Attn: the command is time consuming.
        Args:
            (int): Energy [eV or KeV].
        """
        minE = self.get_property("minE")
        if energy < minE:
            energy = minE
        energy = energy*1000 if energy < 100 else energy

        working_energy_chan = self.get_channel_object("photon_energy")
        working_energy = working_energy_chan.get_value()
        if abs(working_energy - energy) > 99:
            working_energy_chan.set_value(int(egy))

    @task
    def set_detector_filenames(self, frame_number, start, filename):
        """Construct the file name (full path) where the date will be saved.
        Args:
            frame_number(int): The frame number
            start (): Not used, but kept for competeness
            filename (str): The root name.
        """
        print(f"Unused but kept for completeness: start {start}")
        prefix, suffix = os.path.splitext(os.path.basename(filename))
        prefix = "_".join(prefix.split("_")[:-1]) + "_"
        dirname = os.path.dirname(filename)
        if dirname.startswith(os.path.sep):
            dirname = dirname[len(os.path.sep) :]

        saving_directory = os.path.join(self.get_property("buffer"), dirname)

        self.wait_ready()

        self.get_channel_object("saving_directory").set_value(saving_directory)
        self.get_channel_object("saving_prefix").set_value(
            prefix + "%01d" % frame_number
        )
        self.get_channel_object("saving_suffix").set_value(suffix)
        # self.get_channel_object("saving_next_number").set_value(frame_number)
        # self.get_channel_object("saving_index_format").set_value("%04d")
        self.get_channel_object("saving_format").set_value("HDF5")

    def start_acquisition(self):
        """Start the acquisition.
        """
        logging.getLogger("user_level_log").info("Preparing acquisition")
        self.get_command_object("prepare_acq")()
        logging.getLogger("user_level_log").info("Detector ready, continuing")
        self.get_command_object("start_acq")()
        self._emit_status()

    def stop_acquisition(self):
        """Stop the acquisition (stop gracefully).
        """
        try:
            self.get_command_object("stop_acq")()
        except Exception:
            pass

        sleep(1)
        self.get_command_object("reset")()
        self.wait_ready()
        self._emit_status()

    def reset(self):
        """Reset the acquisition (stop immediately).
        """
        self.stop_acquisition()

    @property
    def status(self):
        """Get the status of the acquisition.
        Returns:
            (dict): {"acq_satus": status}.
        """
        try:
            acq_status = self.get_channel_value("acq_status")
        except Exception:
            acq_status = "OFFLINE"

        status = {"acq_satus": acq_status.upper()}

        return status

    def _emit_status(self):
        """Emit statusChanged"""
        self.emit("statusChanged", self.status)

    def recover_from_failure(self):
        """Recover from failure"""
