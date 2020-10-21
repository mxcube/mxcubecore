import shutil
import logging
import os
import decimal
import time


from HardwareRepository.TaskUtils import task
from .ESRFMultiCollect import ESRFMultiCollect, FixedEnergy, PixelDetector
from HardwareRepository.HardwareObjects.LimaPilatusDetector import LimaPilatusDetector


class ID30A1MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, FixedEnergy(0.966, 12.8353))

        self.helical = False

    @task
    def data_collection_hook(self, data_collect_parameters):
        oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
        # are we doing shutterless ?
        shutterless = data_collect_parameters.get("shutterless")
        if oscillation_parameters["overlap"] != 0:
            shutterless = False
        self._detector.shutterless = True if shutterless else False
        file_info = data_collect_parameters["fileinfo"]
        diagfile = (
            os.path.join(file_info["directory"], file_info["prefix"])
            + "_%d_diag.dat" % file_info["run_number"]
        )
        self.getObjectByRole("diffractometer").controller.set_diagfile(diagfile)

        # Metadata management
        ESRFMultiCollect.data_collection_hook(self, data_collect_parameters)

    @task
    def get_beam_size(self):
        return self.bl_control.beam_info.get_beam_size()

    @task
    def get_slit_gaps(self):
        return (
            self.bl_control.diffractometer.controller.hgap.position(),
            self.bl_control.diffractometer.controller.vgap.position(),
        )

    @task
    def get_beam_shape(self):
        return self.bl_control.beam_info.get_beam_shape()

    def get_resolution_at_corner(self):
        return self.bl_control.resolution.get_value_at_corner()

    @task
    def move_motors(self, motors_to_move_dict):
        motion = ESRFMultiCollect.move_motors(self, motors_to_move_dict, wait=False)

        cover_task = self.getObjectByRole("eh_controller").detcover.set_out(
            wait=False, timeout=15
        )

        self.getObjectByRole("beamstop").moveToPosition("in")
        self.getObjectByRole("light").wagoOut()

        motion.get()
        cover_task.get()

    @task
    def do_prepare_oscillation(self, *args, **kwargs):
        return

    @task
    def oscil(self, start, end, exptime, npass):
        save_diagnostic = True
        operate_shutter = True
        if self.helical:
            self.getObjectByRole("diffractometer").helical_oscil(
                start,
                end,
                self.helical_pos,
                exptime,
                npass,
                save_diagnostic,
                operate_shutter,
            )
        else:
            self.getObjectByRole("diffractometer").oscil(
                start, end, exptime, npass, save_diagnostic, operate_shutter
            )

    def open_fast_shutter(self):
        self.getObjectByRole("diffractometer").controller.fshut.open()

    def close_fast_shutter(self):
        self.getObjectByRole("diffractometer").controller.fshut.close()

    def set_helical(self, helical_on):
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        self.helical_pos = helical_oscil_pos

    @task
    def prepare_intensity_monitors(self):
        self.getObjectByRole("diffractometer").controller.set_diode_autorange(
            "i0", True, "i1", False
        )
        self.getObjectByRole("diffractometer").controller.diode(True, False)
        i0_range = decimal.Decimal(
            str(self.getObjectByRole("diffractometer").controller.get_diode_range()[0])
        )
        i1_range = float(
            str(i0_range.as_tuple().digits[0])
            + "e"
            + str(len(i0_range.as_tuple().digits[1:]) + i0_range.as_tuple().exponent)
        )
        self.getObjectByRole("diffractometer").controller.set_i1_range(i1_range)
        return

    def get_beam_centre(self):
        return self.bl_control.resolution.get_beam_centre()

    @task
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
                        os.path.join("/data/id30a1/inhouse/opid30a1/", filename), dest
                    )
        except Exception:
            logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)
