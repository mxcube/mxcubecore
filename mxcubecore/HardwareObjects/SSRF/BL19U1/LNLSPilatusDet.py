import time
import logging
import os
import subprocess
import gevent
import requests
import time
from datetime import datetime
import json
import types

from mxcubecore.TaskUtils import task
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.SSRF.BL19U1 import Constants as cts
from mxcubecore.BaseHardwareObjects import HardwareObjectState

from mxcubecore.HardwareObjects.abstract.AbstractDetector import (
    AbstractDetector,
)
import epics

from mxcubecore.utils.pymysql_comm import UsingMysql
from mxcubecore.service.dataItem_service import insert_new_data_to_job

class LNLSPilatusDet(AbstractDetector):
    DET_THRESHOLD = 'det_threshols_energy'
    # DET_STATUS = 'det_status_message'
    DET_WAVELENGTH = 'det_wavelength'
    DET_DETDIST = 'detectorDistance'
    DET_DETDIST_RBV = 'detectorDistance_RBV'
    DET_BEAM_X = 'det_beam_x'
    DET_BEAM_Y = 'det_beam_y'
    USER_BEAM_X = 'user_beam_x'
    USER_BEAM_Y = 'user_beam_y'
    DET_TRANSMISSION = 'det_transmission'
    DET_START_ANGLE = 'det_start_angle'
    DET_ANGLE_INCR = 'det_angle_incr'

    def __init__(self, name):
        """
        Descript. :
        """
        AbstractDetector.__init__(self, name)
        self.col_config = None
        self.header = dict()
        self.start_angles = list()
        self.col_config = None

    def init(self):
        """
        Descript. :
        """
        AbstractDetector.init(self)

        # self.distance = 500
        self._temperature = 25
        self._humidity = 60
        self.actual_frame_rate = 50
        self._roi_modes_list = ("0", "C2", "C16")
        self._roi_mode = 0
        self._exposure_time_limits = [0.04, 60000]
        self.status = "ready"
        self.pv_status = epics.PV(self.getProperty("channel_status"))
        self.threshold = -1  # Starts with invalid value. To be set.
        self.wavelength = -1
        self.det_distance = -1
        self.beam_x = -1
        self.beam_y = -1
        self.default_beam_x = float(self.getProperty("default_beam_x"))
        self.default_beam_y = float(self.getProperty("default_beam_y"))
        self._distance_motor_hwobj = self.get_object_by_role("detector_distance")
        self.threshold = self.get_threshold_energy()

        self.col_config = {
            "omega_start": 0,
            "omega_increment": 0.1,
            "beam_center_x": 2000,  # length not pixel
            "beam_center_y": 2000,
            "detector_distance": 0.15,
            "count_time": 0.1,
            "nimages": 10,
            "ntrigger": 1,
            # "nimages_per_file": {"value": 100, "api_name": "filewriter"},
            # "roi_mode": "disabled",
            "name_pattern": {"value": "test", "api_name": "filewriter"},
            "photon_energy": 12000,
            # "trigger_mode": "inte",
            "trigger_mode": "exts",
        }

        # 2024.01.12每次重启将此两个epics变量设为0
        self.set_channel_value("phi_increasement", 0)
        self.set_channel_value("omega_increasement", 0)

    def set_roi_mode(self, roi_mode):
        self._roi_mode = roi_mode
        self.emit("detectorModeChanged", (self._roi_mode,))

    def has_shutterless(self):
        """Returns always True
        """
        return True

    def get_beam_position(self, distance=None, wavelength=None):
        """Get approx detector centre """
        xval, yval = super(LNLSPilatusDet, self).get_beam_position(distance=distance)
        if None in (xval, yval):
            # default to Pilatus values
            xval = self.getProperty("width", 2463) / 2.0 + 0.4
            yval = self.getProperty("height", 2527) / 2.0 + 0.4
        return xval, yval

    # def get_beam_position(self, distance=None, wavelength=None):
    #     """Get approx detector centre """
    #     xval = self.getProperty("bx")
    #     yval = self.getProperty("by")
    #     return xval, yval

    def update_values(self):
        self.emit("detectorModeChanged", (self._roi_mode,))
        self.emit("temperatureChanged", (self._temperature, True))
        self.emit("humidityChanged", (self._humidity, True))
        self.emit("expTimeLimitsChanged", (self._exposure_time_limits,))
        self.emit("frameRateChanged", self.actual_frame_rate)
        self.emit("statusChanged", (self.status, "Ready"))

    # def prepare_acquisition(self, *args, **kwargs):
    #     """
    #     Prepares detector for acquisition
    #     """
    #     return

    def last_image_saved(self):
        """
        Returns:
            str: path to last image
        """
        return

    # def start_acquisition(self):
    #     """
    #     Starts acquisition
    #     """
    #     return

    # def stop_acquisition(self):
    #     """
    #     Stops acquisition
    #     """
    #     return

    def get_threshold_energy(self):
        """
        Returns:
            float: threshold energy
        """
        value = float(self.get_channel_value(self.DET_THRESHOLD))
        return value

    def set_threshold_energy(self, energy):
        """
        Set threshold energy and returns whether it was successful or not.
        """
        try:
            float(energy)
        except Exception as e:
            logging.getLogger("HWR").error(
                "Error while setting Pilatus threshold. Value must be float."
            )
            return False

        target_threshold = energy / 2
        if abs(self.get_threshold_energy() - target_threshold) < 0.0001:
            return True

        logging.getLogger("HWR").info("Setting Pilatus threshold...")
        for i in range(3):
            logging.getLogger("user_level_log").info(
                "Setting Pilatus threshold..."
            )

        self.set_channel_value(self.DET_THRESHOLD, target_threshold)

        # wait for threshold setting to be done
        time.sleep(2)
        # Using epics because we need 'as_string' option
        status = self.pv_status.get(as_string=True)
        logging.getLogger("HWR").info('Pilatus status: %s' % status)

        while status == "Setting threshold":
            logging.getLogger("HWR").info(
                'Pilatus status: %s (this may take a minute)...' % status
            )
            time.sleep(3)
            status = self.pv_status.get(as_string=True)

        self.threshold = self.get_threshold_energy()
        logging.getLogger("HWR").info(
            'Pilatus: current threshold is %s (target is %s)' %
            (self.threshold, target_threshold)
        )
        if (status == "Camserver returned OK"
                and self.threshold == target_threshold):
            logging.getLogger("HWR").info('Pilatus status: %s' % status)
            logging.getLogger("HWR").info(
                "Pilatus threshold successfully set."
            )
            return True

        logging.getLogger("HWR").error('Pilatus status: %s' % status)
        logging.getLogger("HWR").error(
            "Error while setting Pilatus threshold. Please, check the detector."
        )
        return False

    def get_wavelength(self):
        """
        Returns:
            float: wavelength
        """
        value = float(self.get_channel_value(self.DET_WAVELENGTH))
        return value

    def set_wavelength(self, wavelength):
        """
        Set wavelength and returns whether it was successful or not.
        """
        try:
            float(wavelength)
        except Exception as e:
            logging.getLogger("HWR").error(
                "Error while setting Pilatus wavelength. Value must be float."
            )
            return False

        # if abs(self.wavelength - wavelength) < 0.0001:
        #    logging.getLogger("HWR").info(
        #        "Pilatus wavelength still okay."
        #    )
        #    return True

        # As the set of Pilatus wavelength, det dist and beam xy is fast,
        # there is no need to compare the target value with the current one.
        logging.getLogger("HWR").info("Setting Pilatus wavelength...")
        self.set_channel_value(self.DET_WAVELENGTH, wavelength)
        time.sleep(0.6)

        print('WAVELENGHT WAS SET: ' + str(wavelength))
        self.wavelength = self.get_wavelength()
        print('WAVELENGHT GOT: ' + str(self.wavelength))

        if abs(self.wavelength - wavelength) < 0.0001:
            logging.getLogger("HWR").info(
                "Pilatus wavelength successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus wavelength. Please, check the detector."
        )
        return False

    def get_detector_distance(self):
        """
        Returns:
            float: detector distance
        """
        value = float(self.get_channel_value(self.DET_DETDIST))
        return value

    def set_detector_distance(self, det_distance):
        """
        Set detector distance and returns whether it was successful or not.
        """
        try:
            float(det_distance)
        except Exception as e:
            logging.getLogger("HWR").error(
                "Error while setting Pilatus det distance. Value must be float."
            )
            return False

        # if abs(self.det_distance - det_distance) < 0.001:
        #    logging.getLogger("HWR").info(
        #        "Pilatus det distance still okay."
        #    )
        #    return True

        logging.getLogger("HWR").info("Setting Pilatus det distance...")
        self.set_channel_value(self.DET_DETDIST, det_distance)
        time.sleep(0.3)

        self.det_distance = self.get_detector_distance()

        if abs(self.det_distance - det_distance) < 0.001:
            logging.getLogger("HWR").info(
                "Pilatus det distance successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus det distance. Please, check the detector."
        )
        return False

    def get_user_beam_x(self):
        """
        Returns:
            float: user beam x
        """
        value = float(self.get_channel_value(self.USER_BEAM_X))
        return value

    def get_beam_x(self):
        """
        Returns:
            float: detector beam x
        """
        value = float(self.get_channel_value(self.DET_BEAM_X))
        return value

    def set_beam_x(self, from_user=False, beam_x=None):
        """
        Set detector beam_x and returns whether it was successful or not.

        Beam X value can come from different sources. The priority (from
        high to low) is:
        * from_user
        * beam_x argument
        * default_beam_x (value set on xml file)
        """
        if from_user:
            logging.getLogger("HWR").info(
                "Getting beam X from user..."
            )
            beam_x = self.get_user_beam_x()

        if beam_x is None:
            if from_user:
                logging.getLogger("HWR").error(
                    "Could not get user beam X. Setting default value (from xml)."
                )
            beam_x = self.default_beam_x

        # if abs(self.beam_x - beam_x) == 0:
        #    logging.getLogger("HWR").info(
        #        "Pilatus beam X still okay."
        #    )
        #    return True

        logging.getLogger("HWR").info("Setting Pilatus beam X to {}...".format(beam_x))
        self.set_channel_value(self.DET_BEAM_X, beam_x)
        time.sleep(1)

        self.beam_x = self.get_beam_x()

        if float(self.beam_x) == float(beam_x):
            logging.getLogger("HWR").info(
                "Pilatus det beam X successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus beam X. Please, check the detector."
        )
        return False

    def get_user_beam_y(self):
        """
        Returns:
            float: user beam y
        """
        value = float(self.get_channel_value(self.USER_BEAM_Y))
        return value

    def get_beam_y(self):
        """
        Returns:
            float: detector beam y
        """
        value = float(self.get_channel_value(self.DET_BEAM_Y))
        return value

    def set_beam_y(self, from_user=False, beam_y=None):
        """
        Set detector beam_y and returns whether it was successful or not.

        Beam Y value can come from different sources. The priority (from
        high to low) is:
        * from_user
        * beam_y argument
        * default_beam_y (value set on xml file)
        """
        if from_user:
            logging.getLogger("HWR").info(
                "Getting beam Y from user..."
            )
            beam_y = self.get_user_beam_y()

        if beam_y is None:
            if from_user:
                logging.getLogger("HWR").error(
                    "Could not get user beam Y. Setting default value (from xml)."
                )
            beam_y = self.default_beam_y

        # if abs(self.beam_y - beam_y) == 0:
        #    logging.getLogger("HWR").info(
        #        "Pilatus beam X still okay."
        #    )
        #    return True

        logging.getLogger("HWR").info("Setting Pilatus beam Y to {}...".format(beam_y))
        self.set_channel_value(self.DET_BEAM_Y, beam_y)
        time.sleep(1)

        self.beam_y = self.get_beam_y()

        if float(self.beam_y) == float(beam_y):
            logging.getLogger("HWR").info(
                "Pilatus det beam Y successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus beam Y. Please, check the detector."
        )
        return False

    def get_transmission(self):
        """
        Returns:
            float: detector filter transmission value
        """
        value = float(self.get_channel_value(self.DET_TRANSMISSION))
        return value

    def set_transmission(self, transmission):
        """
        Set filter transmission and returns whether it was successful or not.
        """
        try:
            float(transmission)
        except Exception as e:
            logging.getLogger("HWR").error(
                "Error while setting Pilatus transmission. Value must be float."
            )
            return False

        logging.getLogger("HWR").info("Setting Pilatus transmission to {}...".format(transmission))
        self.set_channel_value(self.DET_TRANSMISSION, transmission)
        time.sleep(0.3)

        self.transmission = self.get_transmission()

        if abs(self.transmission - transmission) < 0.0001:
            logging.getLogger("HWR").info(
                "Pilatus transmission successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus transmission. Please, check the detector."
        )
        return False

    def get_start_angle(self):
        """
        Returns:
            float: detector start angle value
        """
        value = float(self.get_channel_value(self.DET_START_ANGLE))
        return value

    def set_start_angle(self, start_angle):
        """
        Set start angle and returns whether it was successful or not.
        """
        try:
            float(start_angle)
        except Exception as e:
            logging.getLogger("HWR").error(
                "Error while setting Pilatus start angle. Value must be float."
            )
            return False

        logging.getLogger("HWR").info("Setting Pilatus start angle to {}...".format(start_angle))
        self.set_channel_value(self.DET_START_ANGLE, start_angle)
        time.sleep(3)

        self.start_angle = self.get_start_angle()

        if abs(self.start_angle - start_angle) < 0.0001:
            logging.getLogger("HWR").info(
                "Pilatus start angle successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus start angle. Please, check the detector."
        )
        return False

    def get_angle_incr(self):
        """
        Returns:
            float: detector angle increment value
        """
        value = float(self.get_channel_value(self.DET_ANGLE_INCR))
        return value

    def set_angle_incr(self, angle_incr):
        """
        Set angle increment and returns whether it was successful or not.
        """
        try:
            float(angle_incr)
        except Exception as e:
            logging.getLogger("HWR").error(
                "Error while setting Pilatus angle increment. Value must be float."
            )
            return False

        logging.getLogger("HWR").info("Setting Pilatus angle increment to {}...".format(angle_incr))
        self.set_channel_value(self.DET_ANGLE_INCR, angle_incr)
        time.sleep(3)

        self.angle_incr = self.get_angle_incr()

        if abs(self.angle_incr - angle_incr) < 0.0001:
            logging.getLogger("HWR").info(
                "Pilatus angle increment successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus angle increment. Please, check the detector."
        )
        return False

    def get_pixel_size_x(self):
        """
        return sizes of a single pixel along x-axis respectively
        unit, mm
        """

        return 0.000172

    def get_pixel_size_y(self):
        """
        return sizes of a single pixel along x-axis respectively
        unit, mm
        """

        return 0.000172

    # 0：Idle
    # 1：Acquire
    # 2：Readout
    # 3：Saving
    # 4：Aborting
    @property
    def status(self):
        try:
            acq_status = self.get_channel_value("det_status")
        except Exception:
            acq_status = "OFFLINE"
        if acq_status == 0:
            acq_status = "READY"
        elif acq_status == 1:
            acq_status = "BUSY"
        else:
            acq_status = "OFFLINE"
        # status = {
        #     "acq_satus": acq_status.upper(),
        # }
        status = {"acq_satus": acq_status.upper()}
        #     @property
        #     def status(self):
        #         try:
        #             acq_status = self.get_channel_value("det_status")
        #         except Exception:
        #             acq_status = "OFFLINE"
        #         if acq_status == 0:
        #             acq_status = "IDLE"
        #         elif acq_status == 1:
        #             acq_status = "ACQUIRE"
        #         elif acq_status == 2:
        #             acq_status = "READOUT"
        #         elif acq_status == 3:
        #             acq_status = "SAVING"
        #         elif acq_status == 4:
        #             acq_status = "ABORTING"
        #         else:
        #             acq_status = "OFFLINE"
        #         # status = {
        #         #     "acq_satus": acq_status.upper(),
        #         # }
        #         status = {"acq_satus": acq_status.upper()}

        return status

    def emit_status(self):
        self.emit("statusChanged", self.status)

    def set_collection_uuid(self, col_uuid):
        # TODO check if there is equivalent  UUID with this API
        # self.set_channel_value("CollectionUUID", col_uuid)
        pass
    @task
    def set_detector_filenames_characterisation(self,filename,nth_cbf):
        prefix, suffix = os.path.splitext(os.path.basename(filename))
        prefix = "_".join(prefix.split("_")[:-1]) + "_"
        filename = prefix.split(os.path.sep)[-1]    # os.path.sep is '/'
        filename =filename + nth_cbf
        self.set_channel_value("det_filename", filename)
        logging.getLogger("HWR").info('=============filename is %s', filename)

    @task
    def set_detector_filenames(self, frame_number, start, filename, collect_uuid):
        job_id = ""
        try:
            logging.getLogger("HWR").info('=============Start set_detector_filenames')
            logging.getLogger("HWR").info(f'filename of this collection is {filename}')
            # C:\haicoder\haicoder.txt -> ('C:\\haicoder\\haicoder', 'txt')
            prefix, suffix = os.path.splitext(os.path.basename(filename))
            logging.getLogger('HWR').debug(f'the prefix and suffix when set_detector_filenames are {prefix},{suffix} ')
            prefix = "_".join(prefix.split("_")[:-1]) + "_"
            dirname = os.path.dirname(filename)
            if dirname.startswith(os.path.sep):
                dirname = dirname[len(os.path.sep):]
            logging.getLogger('HWR').debug(f'the dirname when set_detector_filenames are {dirname}')

            saving_directory = os.path.join(self.getProperty("buffer"), dirname)
            logging.getLogger('HWR').debug(f'the saving_directory when set_detector_filenames are {saving_directory}')

            logging.getLogger("HWR").info('=============Start subprocess')
            logging.getLogger("HWR").info("ssh %s@%s mkdir --parents %s" % (
            self.getProperty("user"), self.getProperty("control"), saving_directory))
            subprocess.Popen(
                "ssh %s@%s mkdir --parents %s"
                # % (os.environ["USER"], self.getProperty("control"), saving_directory),
                % (self.getProperty("user"), self.getProperty("control"), saving_directory),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True,
            ).wait()
            logging.getLogger("HWR").info('=============Start set_channel_value')
            self.set_channel_value("saving_directory", saving_directory)
            # self.set_channel_value("saving_prefix", prefix)
            # self.set_channel_value("saving_suffix", suffix)
            # self.set_channel_value("saving_next_number", start)
            # self.set_channel_value("saving_index_format", "%07d")
            # self.set_channel_value("saving_format", self.getProperty("file_suffix"))
            # self.set_channel_value("saving_header_delimiter", ["|", ";", ":"])

            # file_template = prefix.split(os.path.sep)[-1] + "%3.3d"+ "." + self.getProperty("file_suffix")
            # file_template = prefix.split(os.path.sep)[-1] + "." + self.getProperty("file_suffix")
            filename = prefix.split(os.path.sep)[-1]    # os.path.sep is '/'
            # filename = filename[:-2]
            self.set_channel_value("det_filename", filename)
            logging.getLogger("HWR").info('=============filename is %s', filename)

            file_template = "%s%s%4.4d.cbf"
            self.set_channel_value("save_file_template", file_template)

            logging.getLogger("HWR").info('=============END set_channel_value')

            headers = list()

            ##############
            for i, start_angle in enumerate(self.start_angles):
                header = "\n%s\n" % self.getProperty("serial")
                header += "# %s\n" % time.strftime("%Y/%b/%d %T")
                header += "\n%s\n" % self.getProperty("sensor")
                header += "\n%s\n" % self.getProperty("pixel_size")
                self.header["Start_angle"] = start_angle

                for key, value in self.header.items():
                    header += "# %s %s\n" % (key, value)

                headers.append("%d : array_data/header_contents|%s;" % (i, header))

            # self.execute_command("set_image_header", headers)
            self.set_image_header()
            logging.getLogger("HWR").info('=============END set_detector_filenames')
            ##############
            logging.getLogger("HWR").info(f'prefix and dirname of this collection are {filename}, {dirname}')
            job_id = self.updateJobStatus(frame_number, collect_uuid, saving_directory, 'START',filename)
        except Exception as ex:
            logging.getLogger("HWR").error(
                "[HWR] Error set_detector_filenames: %s"
                % (ex)
            )
        return job_id,saving_directory


    def setFileNumber(self, number):
        self.set_channel_value("det_filenumber", number)

    def set_image_header(self):
        self.set_channel_value("det_energy_low", "5")
        self.set_channel_value("det_energy_high", "22")
        self.set_channel_value("det_voffset", "0.0000")
        self.set_channel_value("det_flux", self.header["Flux"])
        self.set_channel_value("det_2theta", self.header["Detector_2theta"])
        self.set_channel_value("det_polarization", HWR.beamline.collect.bl_config.polarisation)
        self.set_channel_value("det_alpha", self.header["Alpha"])
        self.set_channel_value("det_kappa", self.header["Kappa"])
        self.set_channel_value("det_phi", self.header["Phi"])
        # self.set_channel_value("det_phi_incr", file_template)
        self.set_channel_value("det_phi_chi", self.header["Chi"])
        # self.set_channel_value("det_phi_chi_incr", file_template)
        # self.set_channel_value("det_phi_omega", file_template)
        # self.set_channel_value("det_phi_omega_incr", file_template)
        self.set_channel_value("det_phi_oscill_axis", self.header["Oscillation_axis"])
        self.set_channel_value("det_num_oscill", self.header["N_oscillations"])
        self.set_channel_value("det_beam_x", )
        # self.set_channel_value("det_beam_y", 1331.00)
        beamy = self.get_beamy()
        self.set_channel_value("det_beam_y", beamy)
        # self.set_channel_value("det_cbf_template_file", file_template)

    def get_beamy(self):
        distance = self.get_detector_distance()
        value = 1279 - 0.0465 * distance / 1000  #20250305
        return round(value, 2)

    def updateJobStatus(self, frame_number, uuid, path, status,filename):
        # data = {}
        # data['uuid'] = uuid
        # data['src'] = path
        # data['dest'] = path
        # data['status'] = status
        # data['completiontime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # addr = '{0}/job/insert'.format(cts.server_address)
        # response = requests.post(addr, json.dumps(data))
        completiontime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


        job_id = insert_new_data_to_job(frame_number,path,path,completiontime,status,uuid,filename)
        return job_id

        # 将下面的代码整合成一个函数，见上一行代码
        # try:
        #     with UsingMysql(log_time=True) as um:
        #
        #
        #         sql = "INSERT INTO job (nimage, src, dest, createtime, status, uuid ) VALUES (%d, '%s', '%s', '%s', '%s', '%s')" % (
        #             frame_number, path, path, completiontime, status, uuid)
        #         um.cursor.execute(sql)
        #         result = um.cursor.fetchall()
        #         logging.getLogger("HWR").debug("[updateJobStatus from LNLSPilatusDet.py] connect to mysql and result: %s", result)
        #
        #
        #
        #
        #
        # except Exception as ex:
        #     logging.getLogger("HWR").error("[COLLECT] Data collection job update failure: %s", ex)

    def start_acquisition(self):
        # try:
        #     HWR.beamline.collect.getObjectByRole("detector_cover").set_out()
        # except Exception:
        #     pass

        # self.wait_ready()
        # self.execute_command("stop_acq")
        # self.execute_command("prepare_acq")
        # self.execute_command("start_acq")

        self.wait_ready()
        self.set_channel_value("det_acq", 0)
        self.set_channel_value("det_acq", 1)
        time.sleep(1)
        self._emit_status()

    def wait_ready(self, timeout=35):
        with gevent.Timeout(timeout, RuntimeError("Detector not ready")):
            # unarmed (Ready): 0, armed: 1
            while self.get_channel_value("det_status") != 0:
                gevent.sleep(1)
                logging.getLogger("HWR").info(
                    "[HWR] INFO ======== detector status: %s"
                    % (self.get_channel_value("det_status"))
                )
            logging.getLogger("HWR").info(
                "[HWR] INFO ======== detector status: %s, the detector is ready"
                % (self.get_channel_value("det_status"))
            )
        # pass
    def wait_armed(self, timeout=35):
        with gevent.Timeout(timeout, RuntimeError("Detector not ready")):
            # unarmed (Ready): 0, armed: 1
            while self.get_channel_value("det_status") != 1:
                gevent.sleep(1)
                logging.getLogger("HWR").info(
                    "[HWR] INFO ======== detector status: %s"
                    % (self.get_channel_value("det_status"))
                )
            logging.getLogger("HWR").info(
                "[HWR] INFO ======== detector status: %s, the detector is armed"
                % (self.get_channel_value("det_status"))
            )


    def getfilenumber(self):
        number = self.get_channel_value("det_filenumber")
        return number

    def get_deadtime(self):
        return float(self.getProperty("deadtime"))

    def set_energy_threshold(self, energy):
        """Set the energy threshold.
        Args:
            energy (int): Energy [eV] or [keV]
        """
        minE = self.getProperty("minE")
        # some versions of Lima Pilatus server take the energy ergument in keV
        # some in eV. From minE we can set a convertion factor.
        factor = 1000 if minE > 100 else 1.

        # energy_threshold = self.get_channel_value("energy_threshold")
        energy_threshold = self.get_channel_value(self.DET_THRESHOLD)

        # check if need to convert energy in eV.
        if energy < 100:
            energy *= factor

        if energy > 100:
            energy = energy / 1000

        if energy < minE:
            energy = minE

        target_threshold = energy / 2
        if abs(energy_threshold - target_threshold) > 0.1:
            self.set_channel_value(self.DET_THRESHOLD, target_threshold)
            while abs(self.get_channel_value(self.DET_THRESHOLD) - target_threshold) > 0.1:
                time.sleep(1)

        # self.set_channel_value("fill_mode", "ON")

    ### 未找到
    # def get_file_list(self):
    #     savednumber = self.get_channel_value('last_image_saved')
    #     logging.getLogger("HWR").info('saved number: %s', savednumber)
    #     return savednumber

    def get_file_list(self):
        arr = self.get_channel_value('last_image_saved')
        s = ''.join([chr(i) for i in arr])
        print("last image saved: ", s)
        arr1 = s.split("_")
        s1 = arr1[len(arr1) - 1]
        arr2 = s1.split(".")
        s2 = arr2[0]
        s3 = self.removeleading(s2)
        savednumber = int(s3)
        logging.getLogger("HWR").info('saved number: %s', savednumber)
        return savednumber

    def removeleading(self, str):
        try:
            while str[0] == "0":
                str = str[1:]
            return str
        except Exception as ex:
            return 0

    def is_exte_enabled(self):
        return self.trigger_mode == "exte"

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
        if osc_range < 1e-4:
            trigger_mode = "0"
        elif mesh:
            trigger_mode = "1"
        else:
            trigger_mode = "2"

        # if osc_range < 1e-4:
        #   trigger_mode = "INTERNAL_TRIGGER"
        # elif mesh:
        # trigger_mode = "EXTERNAL_GATE"
        # else:
        # trigger_mode = "EXTERNAL_TRIGGER"

        diffractometer_positions = HWR.beamline.diffractometer.get_positions()
        logging.getLogger("HWR").info("=========Get Diffractomenter Position End")

        self.start_angles = list()
        for i in range(number_of_images):
            self.start_angles.append("%0.4f deg." % (start + osc_range * i))
        self.header["file_comments"] = comment
        self.header["N_oscillations"] = number_of_images
        self.header["Oscillation_axis"] = "omega"
        # self.header["Chi"] = "0.0000 deg."
        self.header["Chi"] = "0"
        kappa_phi = diffractometer_positions.get("kappa_phi", -9999)
        if kappa_phi is None:
            kappa_phi = -9999
        kappa = diffractometer_positions.get("kappa", -9999)
        if kappa is None:
            kappa = -9999
        # self.header["Phi"] = "%0.4f deg." % kappa_phi
        # self.header["Kappa"] = "%0.4f deg." % kappa
        # self.header["Alpha"] = "0.0000 deg."
        # self.header["Polarization"] = HWR.beamline.collect.bl_config.polarisation
        # self.header["Detector_2theta"] = "0.0000 deg."
        # self.header["Angle_increment"] = "%0.4f deg." % osc_range

        self.header["Phi"] = kappa_phi
        self.header["Kappa"] = kappa
        self.header["Alpha"] = "0.0000"
        self.header["Polarization"] = HWR.beamline.collect.bl_config.polarisation
        self.header["Detector_2theta"] = "0.0000"
        self.header["Angle_increment"] = osc_range

        self.header["Transmission"] = HWR.beamline.transmission.get_value()

        self.header["Flux"] = HWR.beamline.flux.get_value()
        # self.header["Beam_xy"] = "(%.2f, %.2f) pixels" % tuple(
        #     [value / 0.172 for value in HWR.beamline.detector.get_beam_position()]
        # )
        self.header["Beam_xy"] = "(1229.00, 1331.00) pixels"
        self.header["Detector_Voffset"] = "0.0000 m"
        self.header["Energy_range"] = "(7, 20) keV"
        self.header["Detector_distance"] = "%f m" % (self.distance.get_value() / 1000.0)
        self.header["Wavelength"] = "%f A" % HWR.beamline.energy.get_wavelength()
        self.header["Trim_directory:"] = "(nil)"
        self.header["Flat_field:"] = "(nil)"
        self.header["Excluded_pixels:"] = " badpix_mask.tif"
        self.header["N_excluded_pixels:"] = "= 321"
        self.header["Threshold_setting"] = "%d eV" % self.get_channel_value("det_threshols_energy")
        self.header["Count_cutoff"] = "1048500"
        self.header["Tau"] = "= 0 s"
        # self.header["Exposure_period"] = "%f s" % (exptime + self.get_deadtime())
        # self.header["Exposure_time"] = "%f s" % exptime
        self.header["Exposure_period"] = "%f s" % exptime
        self.header["Exposure_time"] = "%f s" % (exptime - self.get_deadtime())

        self.reset()
        logging.getLogger("HWR").info("=========Start wait ready")
        self.wait_ready()
        logging.getLogger("HWR").info("=========End wait ready")

        self.set_energy_threshold(HWR.beamline.energy.get_value())

        self.set_channel_value("acq_trigger_mode", trigger_mode)

        if self.getProperty("set_latency_time", False):
            self.set_channel_value("latency_time", self.get_deadtime())

        ###??? self.set_channel_value("saving_mode", "AUTO_FRAME")
        self.set_channel_value("acq_nb_frames", number_of_images)
        # self.set_channel_value("acq_expo_time", exptime)
        # self.set_channel_value("acq_expo_period", exptime + self.get_deadtime())
        self.set_channel_value("acq_expo_time", exptime - self.get_deadtime())
        self.set_channel_value("acq_expo_period", exptime)
        ###??? self.set_channel_value("saving_overwrite_policy", "OVERWRITE")
        self.set_channel_value("det_phi_omega", start)
        self.set_channel_value("det_phi_omega_incr", osc_range)

    def reset(self):
        try:
            self.stop_acquisition()
        except Exception as e:
            logging.getLogger("HWR").error(
                "Error while stop acquisition. %s", e
            )

    def stop_acquisition(self):
        try:
            logging.getLogger("HWR").info(
                "################# stop_acquisition start ################"
            )
            logging.getLogger("HWR").info(
                "################# det_acq 0 ################"
            )
            # self.execute_command("stop_acq")
            # self.set_channel_value("det_status", 0)
            self.set_channel_value("det_acq", 0)

            logging.getLogger("HWR").info(
                "################# stop_acquisition end ################"
            )
        except Exception as ex:
            print(ex)

        time.sleep(2)
        ###### ？？？
        # self.execute_command("reset")
        ###### ？？？
        logging.getLogger("HWR").info(
            "################# warit ready start ################"
        )
        self.wait_ready()
        logging.getLogger("HWR").info(
            "################# warit ready end ################"
        )
        self._emit_status()

    def _emit_status(self):
        self.emit("statusChanged", self.status)

    def set_cam1_distance(self):
        try:
            value = self.get_channel_value(self.DET_DETDIST)
            logging.getLogger("HWR").info("get epics detect distance: %s", value)

            setvalue = 0;
            if type(value) == int:
                if value > 100:
                    setvalue = value / 1000
            else:
                setvalue = int(value)
                if value > 100:
                    setvalue = value / 1000
            logging.getLogger("HWR").info("detect distance: %s", str(setvalue))
            self.set_channel_value("cam1_distance", setvalue)
            tolerance = float(self.getProperty("tolerance"))
            time.sleep(2)
            rtnValue = self.getDistnaceRtnValue()
            time.sleep(1)
            rtnValue1 = self.getDistnaceRtnValue()

            while abs(rtnValue - setvalue) > tolerance and rtnValue != rtnValue1:
                time.sleep(1)
                rtnValue = self.getDistnaceRtnValue()
                time.sleep(1)
                rtnValue1 = self.getDistnaceRtnValue()
                logging.getLogger("HWR").info(
                    "set value: %s, RBV value: %s, RBV value 1: %s " % (str(setvalue), str(rtnValue), str(rtnValue)))

            logging.getLogger("HWR").info("set detect distance success, RBV value: %s" % str(rtnValue))

        except Exception as ex:
            logging.getLogger("HWR").info("set detect distance: %s", ex)

    def getDistnaceRtnValue(self):
        rtnValue = self.get_channel_value(self.DET_DETDIST_RBV)
        if rtnValue > 1000:
            rtnValue = rtnValue / 1000
        logging.getLogger("HWR").info("RBV value: %s" % str(rtnValue))
        return rtnValue

    # def restart(self) -> None:
    #     self.update_state(HardwareObjectState.BUSY)
    #     time.sleep(2)
    #     self.update_state(HardwareObjectState.READY)