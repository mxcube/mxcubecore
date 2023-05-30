#! /usr/bin/env python
# encoding: utf-8
"""Collection emulator, calling an external program to generate data images.
Written originally for Global Phasing simcal,
but could be made to work with other systems

License:

This file is part of MXCuBE.

MXCuBE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MXCuBE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.
"""

import os
import subprocess
import logging
import re
from collections import OrderedDict
import f90nml
from mxcubecore.utils import conversion
from mxcubecore.HardwareObjects.mockup.CollectMockup import CollectMockup
from mxcubecore.TaskUtils import task

from mxcubecore import HardwareRepository as HWR

__copyright__ = """ Copyright © 2017 - 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"


class CollectEmulator(CollectMockup):
    def __init__(self, name):
        CollectMockup.__init__(self, name)

        self.instrument_data = None
        self.segments = None

        self._counter = 1

    # def init(self):
    #     CollectMockup.init(self)
    #     # NBNB you get an error if you use 'HWR.beamline.session'
    #     # session_hwobj = self.get_object_by_role("session")
    #     session = HWR.beamline.session
    #     if session and self.has_object("override_data_directories"):
    #         dirs = self["override_data_directories"].get_properties()
    #         session.set_base_data_directories(**dirs)

    def _get_simcal_input(self, data_collect_parameters, crystal_data):
        """Get ordered dict with simcal input from available data"""

        # Set up and add crystal data
        result = OrderedDict()
        setup_data = result["setup_list"] = crystal_data

        if self.instrument_data is None:
            # Read instrumentation.nml and put data into mock objects
            # NB if we are here we must be in mock mode.
            #
            # update with instrument data
            # You cannot do this at init time,
            # as GPhL_wporkflow is not yet inittialised then.
            fp0 = HWR.beamline.gphl_workflow.file_paths.get("instrumentation_file")
            instrument_input = f90nml.read(fp0)

            self.instrument_data = instrument_input["sdcp_instrument_list"]
            self.segments = instrument_input["segment_list"]

        #
        # # update with instrument data
        # fp0 = HWR.beamline.gphl_workflow.file_paths.get("instrumentation_file")
        # instrument_input = f90nml.read(fp0)
        #
        # instrument_data = instrument_input["sdcp_instrument_list"]
        # segments = instrument_input["segment_list"]
        if isinstance(self.segments, dict):
            segment_count = 1
        else:
            segment_count = len(self.segments)

        sweep_count = len(data_collect_parameters["oscillation_sequence"])

        # Move beamstop settings to top level
        ll0 = self.instrument_data.get("beamstop_param_names")
        ll1 = self.instrument_data.get("beamstop_param_vals")
        if ll0 and ll1:
            for tag, val in zip(ll0, ll1):
                self.instrument_data[tag.lower()] = val

        # Setting parameters in order (may not be necessary, but ...)
        # Missing: *mu*
        remap = {
            "beam": "nominal_beam_dir",
            "det_coord_def": "det_org_dist",
            "cone_s_height": "cone_height",
        }
        tags = (
            "lambda_sd",
            "beam",
            "beam_sd_deg",
            "pol_plane_n",
            "pol_frac",
            "d_sensor",
            "min_zeta",
            "det_name",
            "det_x_axis",
            "det_y_axis",
            "det_qx",
            "det_qy",
            "det_nx",
            "det_ny",
            # "det_org_x",
            # "det_org_y",
            "det_coord_def",
        )
        for tag in tags:
            val = self.instrument_data.get(remap.get(tag, tag))
            if val is not None:
                setup_data[tag] = val

        (
            setup_data["det_org_x"],
            setup_data["det_org_y"],
        ) = HWR.beamline.detector.get_beam_position()

        ll0 = self.instrument_data["gonio_axis_dirs"]
        setup_data["omega_axis"] = ll0[:3]
        setup_data["kappa_axis"] = ll0[3:6]
        setup_data["phi_axis"] = ll0[6:]
        ll0 = self.instrument_data["gonio_centring_axis_dirs"]
        setup_data["trans_x_axis"] = ll0[:3]
        setup_data["trans_y_axis"] = ll0[3:6]
        setup_data["trans_z_axis"] = ll0[6:]
        tags = (
            "cone_radius",
            "cone_s_height",
            "beam_stop_radius",
            "beam_stop_s_length",
            "beam_stop_s_distance",
        )
        for tag in tags:
            val = self.instrument_data.get(remap.get(tag, tag))
            if val is not None:
                setup_data[tag] = val

        # Add/overwrite parameters from emulator configuration
        conv = conversion.convert_string_value
        for key, val in self["simcal_parameters"].get_properties().items():
            setup_data[key] = conv(val)

        setup_data["n_vertices"] = 0
        setup_data["n_triangles"] = 0
        setup_data["n_segments"] = segment_count
        setup_data["n_orients"] = 0
        setup_data["n_sweeps"] = sweep_count

        # Add segments
        result["segment_list"] = self.segments

        # Adjustments
        val = self.instrument_data.get("beam")
        if val:
            setup_data["beam"] = val

        # update with diffractcal data
        # TODO check that this works also for updating segment list
        fp0 = HWR.beamline.gphl_workflow.file_paths.get("diffractcal_file")
        if os.path.isfile(fp0):
            diffractcal_data = f90nml.read(fp0)["sdcp_instrument_list"]
            for tag in setup_data.keys():
                val = diffractcal_data.get(tag)
                if val is not None:
                    setup_data[tag] = val
            ll0 = diffractcal_data["gonio_axis_dirs"]
            setup_data["omega_axis"] = ll0[:3]
            setup_data["kappa_axis"] = ll0[3:6]
            setup_data["phi_axis"] = ll0[6:]

        # get resolution limit and detector distance
        detector_distance = data_collect_parameters.get("detector_distance", 0.0)
        if not detector_distance:
            dd = data_collect_parameters.get("resolution")
            # resolution may not be set - if so you should take the current value
            if dd:
                resolution = dd.get("upper")
                if resolution:
                    self.set_resolution(resolution)
            detector_distance = HWR.beamline.detector.distance.get_value()
        # Add sweeps
        sweeps = []
        compress_data = False
        for osc in data_collect_parameters["oscillation_sequence"]:
            motors = data_collect_parameters["motors"]
            sweep = OrderedDict()

            energy = (
                data_collect_parameters.get("energy") or HWR.beamline.energy.get_value()
            )
            sweep["lambda"] = conversion.HC_OVER_E / energy
            sweep["res_limit"] = setup_data["res_limit_def"]
            sweep["exposure"] = osc["exposure_time"]
            ll0 = HWR.beamline.gphl_workflow.translation_axis_roles
            sweep["trans_xyz"] = list(motors.get(x) or 0.0 for x in ll0)
            sweep["det_coord"] = detector_distance
            # NBNB hardwired for omega scan TODO
            sweep["axis_no"] = 3
            sweep["omega_deg"] = osc["start"]
            # NB kappa and phi are overwritten from the motors dict, if set there
            sweep["kappa_deg"] = osc["kappaStart"]
            sweep["phi_deg"] = osc["phiStart"]
            sweep["step_deg"] = osc["range"]
            sweep["n_frames"] = osc["number_of_images"]
            sweep["image_no"] = osc["start_image_number"]
            # self.make_image_file_template(data_collect_parameters, suffix='cbf')

            # Extract format statement from template,
            # and convert to fortran format
            text_type = conversion.text_type
            template = text_type(data_collect_parameters["fileinfo"]["template"])
            ss0 = re.search("(%[0-9]+d)", template).group(0)
            template = template.replace(ss0, "?" * int(ss0[1:-1]))
            name_template = os.path.join(
                text_type(data_collect_parameters["fileinfo"]["directory"]),
                template
                # data_collect_parameters['fileinfo']['template']
            )
            # We still use the normal name template for compressed data
            if name_template.endswith(".gz"):
                compress_data = True
                name_template = name_template[:-3]
            sweep["name_template"] = name_template

            # Overwrite kappa and phi from motors - if set
            val = motors.get("kappa")
            if val is not None:
                sweep["kappa_deg"] = val
            val = motors.get("kappa_phi")
            if val is not None:
                sweep["phi_deg"] = val

            # Skipped: spindle_deg=0.0, two_theta_deg=0.0, mu_air=-1, mu_sensor=-1

            sweeps.append(sweep)

        if sweep_count == 1:
            # NBNB in current code we can have only one sweep here,
            # but it will work for multiple
            result["sweep_list"] = sweep
        else:
            result["sweep_list"] = sweeps
        #
        return result, compress_data

    @task
    def data_collection_hook(self):
        """Spawns data emulation using gphl simcal"""

        data_collect_parameters = self.current_dc_parameters

        if not HWR.beamline.gphl_workflow:
            raise ValueError("Emulator requires GΦL workflow installation")
        gphl_connection = HWR.beamline.gphl_connection
        if not gphl_connection:
            raise ValueError("Emulator requires GΦL connection installation")

        # Get program locations
        simcal_executive = gphl_connection.get_executable("simcal")
        simcal_licence_dir = (
            gphl_connection.get_bdg_licence_dir("simcal")
            or gphl_connection.software_paths["GPHL_INSTALLATION"]
        )
        # # Get environmental variables.
        envs = {"autoPROC_home": simcal_licence_dir}
        GPHL_XDS_PATH = gphl_connection.software_paths.get("GPHL_XDS_PATH")
        if GPHL_XDS_PATH:
            envs["GPHL_XDS_PATH"] = GPHL_XDS_PATH
        GPHL_CCP4_PATH = gphl_connection.software_paths.get("GPHL_CCP4_PATH")
        if GPHL_CCP4_PATH:
            envs["GPHL_CCP4_PATH"] = GPHL_CCP4_PATH
        text_type = conversion.text_type
        for tag, val in self["environment_variables"].get_properties().items():
            envs[text_type(tag)] = text_type(val)

        # get crystal data
        crystal_data, hklfile = HWR.beamline.gphl_workflow.get_emulation_crystal_data()

        input_data, compress_data = self._get_simcal_input(
            data_collect_parameters, crystal_data
        )

        # NB outfile is the echo output of the input file;
        # image files templates are set in the input file
        file_info = data_collect_parameters["fileinfo"]
        if not os.path.exists(file_info["directory"]):
            os.makedirs(file_info["directory"])
        infile = os.path.join(
            file_info["directory"], "simcal_in_%s.nml" % self._counter
        )

        f90nml.write(input_data, infile, force=True)
        outfile = os.path.join(
            file_info["directory"], "simcal_out_%s.nml" % self._counter
        )
        logfile = os.path.join(
            file_info["directory"], "simcal_log_%s.txt" % self._counter
        )
        self._counter += 1
        command_list = [
            simcal_executive,
            "--input",
            infile,
            "--output",
            outfile,
            "--hkl",
            hklfile,
        ]

        for tag, val in self["simcal_options"].get_properties().items():
            command_list.extend(conversion.command_option(tag, val, prefix="--"))
        logging.getLogger("HWR").info("Executing command: %s", " ".join(command_list))
        logging.getLogger("HWR").info("Executing environment: %s", sorted(envs.items()))

        if compress_data:
            command_list.append("--gzip-img")

        fp1 = open(logfile, "w")
        fp2 = subprocess.STDOUT
        # resource.setrlimit(resource.RLIMIT_STACK, (-1,-1))

        def set_ulimit():
            import resource

            resource.setrlimit(
                resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
            )

        try:
            self.emit("collectStarted", (None, 1))
            running_process = subprocess.Popen(
                command_list, stdout=fp1, stderr=fp2, env=envs, preexec_fn=set_ulimit
            )
            gphl_connection.collect_emulator_process = running_process

            # # NBNB leaving this in causes simulations to be killed and missing images
            # super(CollectEmulator, self).data_collection_hook()

            logging.getLogger("HWR").info("Waiting for simcal collection emulation.")
            # NBNB TODO put in time-out, somehow
            return_code = running_process.wait()
        except Exception:
            logging.getLogger("HWR").error("Error in GΦL collection emulation")
            raise
        finally:
            fp1.close()
        process = gphl_connection.collect_emulator_process
        gphl_connection.collect_emulator_process = None
        if process == "ABORTED":
            logging.getLogger("HWR").info("Simcal collection emulation aborted")
        elif return_code:
            raise RuntimeError(
                "simcal process terminated with return code %s" % return_code
            )
        else:
            logging.getLogger("HWR").info("Simcal collection emulation successful")
        self.ready_event.set()
        #
        return
