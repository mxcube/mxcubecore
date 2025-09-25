# encoding: utf-8
#
#  Project name: MXCuBE
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

"""Collect procedures, using bliss for scanning
Example xml configuration:

.. code-block:: xml

 <object class="ESRF.ESRFMultiCollect">
   <username>Photon flux</username>
   <object role="controller" href="/bliss"/>
   <scan_object>md2scan</scan_object>
   <num_snapshots>4</num_snapshots>
   <geometry>[-1, 0, 0, 0, -1, 0]</geometry>
 </object>
"""

import logging
import os
import shutil
from ast import literal_eval

from mxcubecore import HardwareRepository as HWR

from .ESRFMultiCollect import ESRFMultiCollect
from .fill_meta_data import FillMetaData
from lima2mxh5master.api import convert_lima2_to_h5mx
from pathlib import Path

class BlissMultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        super().__init__(name)
        self.fast_characterisation = None
        self.geometry = []
        self.metadata = None
        self._data_collect_parameters = None
        self.last_bliss_scan = None

    def init(self):
        super().init()
        # self.number_of_snapshots = self.get_property("num_snapshots", 4)
        _bliss = self.get_object_by_role("controller")
        _name = self.get_property("scan_object")

        # this is the geometry of the diffractometer
        try:
            self.geometry = literal_eval(self.get_property("geometry"))
        except ValueError:
            self.geometry = [-1, 0, 0, 0, -1, 0]
        self._scan = getattr(_bliss, _name)
        self.metadata = FillMetaData()

    def data_collection_hook(self, data_collect_parameters):
        pass

    def data_collection_end_hook(self, data_collect_parameters):
        self._detector._emit_status()

        oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
        subwedge_size = oscillation_parameters.get("reference_interval", 1)
        wedges_to_collect = self.prepare_wedges_to_collect(
            oscillation_parameters["start"],
            oscillation_parameters["number_of_images"],
            oscillation_parameters["range"],
            subwedge_size,
            oscillation_parameters["overlap"]
        )

        for wedge_number in range(1, len(wedges_to_collect) + 1):
            print("Calling convert_lima2_to_h5mx with %s %s %s" % (
                  Path(self.last_bliss_scan.scan_saving.data_fullpath),
                  Path(self.last_bliss_scan.scan_saving.get_path(),
                     data_collect_parameters["fileinfo"]["prefix"]+"_1_%s_master.h5" % wedge_number
                  ),
                  "%s.1" % wedge_number
                )
            )

            convert_lima2_to_h5mx(
                Path(self.last_bliss_scan.scan_saving.data_fullpath),
                Path(self.last_bliss_scan.scan_saving.get_path(),
                     data_collect_parameters["fileinfo"]["prefix"]+"_1_%s_master.h5" % wedge_number
                ),
                "%s.1" % wedge_number
            )

    def _bliss_data_collection_hook(self, data_collect_parameters):
        # first set the proposal name for bliss
        _as = HWR.beamline.lims.get_active_session()
        proposal = f"{_as.code}{_as.number}"
        self._scan.set_session(proposal)

        sample_name = data_collect_parameters["sample_reference"]["sample_name"]
        meta_data = {
            "sample_name": sample_name.replace(":", "-"),
            "acronym": data_collect_parameters["sample_reference"]["acronym"],
            "subdir": data_collect_parameters["fileinfo"]["directory"].split("RAW_DATA/")[1],
        }

        # fill in the static metadata
        self._scan.prepare_data_saving(meta_data)
        self.metadata.diffractometer_static_data()
        self.metadata.detector_static_data()

        try:
            comment = HWR.beamline.sample_changer.get_crystal_id()
            data_collect_parameters["comment"] = comment
        except AttributeError:
            pass

    def last_image_saved(self, total_time, exptime, num_images):
        if self._scan._lima_object.tango_ctrl_dev.acq_state == "running":
            # if HWR.beamline.detector.status["acq_satus"] == "RUNNING":
            return int(total_time / exptime)
        else:
            # return HWR.beamline.detector.last_image_saved()   
            return num_images

    def get_beam_size(self):
        _width, _height, _, _ = HWR.beamline.beam.get_value()
        return _width, _height

    def get_slit_gaps(self):
        return (None, None)

    def get_beam_shape(self):
        return HWR.beamline.beam.get_value()[2].name

    def get_resolution_at_corner(self):
        return HWR.beamline.resolution.get_value_at_corner()

    def ready(*motors):
        return not any([m.motorIsMoving() for m in motors])

    def move_motors(self, motors_to_move_dict):
        # We do not want to modify the input dict
        motor_positions_copy = motors_to_move_dict.copy()
        diffr = HWR.beamline.diffractometer
        for tag in ("kappa", "kappa_phi", "zoom"):
            if tag in motor_positions_copy:
                del motor_positions_copy[tag]

        diffr.move_sync_motors(motor_positions_copy, wait=True, timeout=200)

    def take_crystal_snapshots(self, number_of_snapshots, image_path_list=[]):
        HWR.beamline.diffractometer.take_snapshot(image_path_list)

    def do_prepare_oscillation(self, *args, **kwargs):
        diffr = HWR.beamline.diffractometer
        print("Preparing oscillation.............")
        # set the detector cover out
        try:
            diffr.open_detector_cover()
        except Exception:
            logging.getLogger("HWR").exception("Could not open detector cover")

        # send again the command as MD2 software only handles one
        # centered position!!
        # has to be where the motors are and before changing the phase
        # diffr.get_command_object("save_centring_positions")()

        # switch on the front light
        front_light_switch = diffr.get_object_by_role("FrontLightSwitch")
        front_light_switch.set_value(front_light_switch.VALUES.IN)
        # diffr.get_object_by_role("FrontLight").set_value(2)

        # move to DataCollection phase
        logging.getLogger("user_level_log").info("Moving MD2 to DataCollection")
        # AB next line to speed up the data collection
        diffr.set_phase("DataCollection", wait=False, timeout=0)

    def data_collection_cleanup(self):
        self.close_fast_shutter()

    def diffractometer_metadata(self, start, end, exptime, nb_images):
        """Prepare the diffractometer related meta data"."""
        self.metadata.diffractometer_static_data()
        self.metadata.geometry["orientation"]["value"] = self.geometry

    def detector_metadata(self, start, end, exptime, nb_images):
        """Prepare the detector related meta data"."""
        self.metadata.detector_static_data()
        self.metadata.detector_specific[
            "x_pixels_in_detector"
        ] = HWR.beamline.detector.get_width()
        self.metadata.detector_specific[
            "y_pixels_in_detector"
        ] = HWR.beamline.detector.get_height()
        self.metadata.detector_specific[
            "photon_energy"
        ] = HWR.beamline.energy.get_value()
        
        self.metadata.detector[
        "detector_specific"
        ] = self.metadata.detector_specific

        pixel_size_x, pixel_size_y = HWR.beamline.detector.get_pixel_size()
        beam_x, beam_y = HWR.beamline.detector.get_beam_position()
        readout_time = HWR.beamline.detector.get_property("deadtime")

        self.metadata.detector.update({
            "detector": {
                "beam_center_x": beam_x,
                "beam_center_x@units": "pixel",
                "beam_center_y": beam_y,
                "beam_center_y@units": "pixel",
                "count_time": exptime/nb_images,
                "count_time@units": "s",
                "frame_time": (exptime/nb_images) + readout_time,
                "readout_time": readout_time,
                "readout_time@units": "s",
                "frame_time@units": "s",
                "distance": HWR.beamline.detector.distance.get_value()/ 1000.0,
                "distance@units": "m",
                "nimages": nb_images,
                "x_pixel_size": pixel_size_x / 1000.0,
                "x_pixel_size@units": "m",
                "y_pixel_size": pixel_size_y / 1000.0,
                "y_pixel_size@units": "m",
                "counter_name": "pilatus4_4m_lima2",
                "detector_number": "D029099",
            }
          }
        )

    def sample_metadata(self, start, end, exptime, nb_images) -> dict:
        """Prepare the meta data for the sample"""
        omega = []
        omega_end = []
        meta_data = {}
        osc_range_total = abs(end - start)
        osc_range = osc_range_total / nb_images
        for img in range(nb_images):
            omega.append(start + img * osc_range)
            omega_end.append(start + (img + 1) * osc_range)

        self.metadata.sample_transformations.update(
            {
                "transformations": {
                    "omega": omega,
                    "omega_end": omega_end,
                    "omega_range_average": osc_range,
                    "omega_range_total": osc_range_total,
                    "omega@vector": self.geometry[:3],
                    "omega@unit": "deg",
                    "omega_end@unit": "deg",
                    "omega_range_average@unit": "deg",
                    "omega_range_total@unit": "deg",
                    "translation": [0] ,
                }
            }
        )
        self.metadata.sample_goniometer.update(
            {
                "goniometer": {
                    "omega": omega,
                    "omega_end": omega_end,
                    "omega_range_average": osc_range,
                    "omega_range_total": osc_range_total,
                }
            }
        )

    def beam_metadata(self):
        """Meta data for the beam"""
        self.metadata.beam.update(
            {
                "beam": {
                    "incident_wavelength": HWR.beamline.energy.get_wavelength(),
                    "incident_wavelength@units": "angstrom"
                }
            }
        )
        
    def oscil(self, start, end, exptime, nb_images, wait=True):
        """run bliss scan according to the type"""
        print("---------------->", start, end, exptime, nb_images)

        meta_data = {}
        self.sample_metadata(start, end, exptime, nb_images)
        self.beam_metadata()
        self.detector_metadata(start, end, exptime, nb_images)
        #self.diffractometer_metadata(start, end, exptime, nb_images)
        meta_data = self.metadata

        if self.helical:
            # helical scan
            motor_pos = self.helical_pos
            self.last_bliss_scan = self._scan.line_scan(start, end, exptime, nb_images, motor_pos, meta_data)
        elif self.mesh:
            # ??? nb_images = self.mesh_total_nb_frames
            # move the motorts to the centre of the mesh first
            HWR.beamline.diffractometer.move_motors(self.mesh_center.as_dict())
            print("------------>", self.mesh_range, type(self.mesh_range))
            self.last_bliss_scan = self._scan.mesh_scan(
                start,
                end,
                exptime,
                nb_images,
                self.mesh_num_lines,
                self.mesh_range,
                meta_data,
            )
        elif self.fast_characterisation:
            self.nb_frames = 10
            self.nb_scan = 4
            self.angle = 90
            exptime *= 10
            _end = (end - start) * 10
            self.last_bliss_scan = self._scan.characterisation_scan(
                start,
                _end,
                exptime,
                self.nb_frames,
                self.nb_scan,
                self.angle,
                meta_data,
            )
        else:
            self.last_bliss_scan = self._scan.osc_scan(start, end, exptime, nb_images, meta_data)

    def prepare_acquisition(
        self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""
    ):
        pass

    def start_acquisition(self, exptime, npass, first_frame, shutterless):
        pass

    def open_fast_shutter(self):
        fs = HWR.beamline.fast_shutter
        fs.set_value(fs.VALUES.OPEN)

    def close_fast_shutter(self):
        fs = HWR.beamline.fast_shutter
        fs.set_value(fs.VALUES.CLOSED)

    def set_helical(self, helical_on):
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        self.helical_pos = helical_oscil_pos

    # specifies the next scan will be a mesh scan
    def set_mesh(self, mesh_on):
        self.mesh = mesh_on

    def set_mesh_scan_parameters(
        self, num_lines, total_nb_frames, mesh_center_param, mesh_range_param
    ):
        """
        sets the mesh scan parameters :
         - vertcal range
         - horizontal range
         - nb lines
         - nb frames per line
        """
        self.mesh_num_lines = num_lines
        self.mesh_total_nb_frames = total_nb_frames
        self.mesh_range = mesh_range_param
        self.mesh_center = mesh_center_param

    def set_fast_characterisation(self, value=False):
        self.fast_characterisation = value

    def get_cryo_temperature(self):
        return 0

    def prepare_intensity_monitors(self):
        return

    def get_beam_centre(self):
        pixel_x, pixel_y = HWR.beamline.detector.get_pixel_size()
        bcx, bcy = HWR.beamline.detector.get_beam_position()
        return [bcx * pixel_x, bcy * pixel_y]

    def write_input_files(self, datacollection_id):
        # copy *geo_corr.cbf* files to process directory
        try:
            process_dir = os.path.join(self.xds_directory, "..")
            raw_process_dir = os.path.join(self.raw_data_input_file_dir, "..")
            for dir in (process_dir, raw_process_dir):
                for filename in ("x_geo_corr.cbf.bz2", "y_geo_corr.cbf.bz2"):
                    dest = os.path.join(dir, filename)
                    if os.path.exists(dest):
                        continue
                    shutil.copyfile(
                        os.path.join(
                            self.get_property("template_file_directory"), filename
                        ),
                        dest,
                    )
        except Exception:
            logging.exception("Exception happened while copying geo_corr files")

        return super().write_input_files(datacollection_id)
