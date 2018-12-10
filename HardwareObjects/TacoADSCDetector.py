def grouped(iterable, n):
    "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
    return itertools.izip(*[iter(iterable)] * n)


class ADSC:
    """
        <command type="taco" taconame="id30/adsc/massif1" name="detector_state">DevState</command>
        <command type="taco" taconame="id30/adsc/massif1" name="detector_status">DevStatus</command>
        <command type="taco" taconame="id30/adsc/massif1" name="detector_setfilepar">DevCCDSetFilePar</command>
        <command type="taco" taconame="id30/adsc/massif1" name="detector_sethwpar">DevCCDSetHwPar</command>
        <command type="taco" taconame="id30/adsc/massif1" name="detector_stop">DevCCDStopExposure</command>
        <command type="taco" taconame="id30/adsc/massif1" name="detector_write_image">DevCCDWriteImage</command>
        <command type="taco" taconame="id30/adsc/massif1" name="detector_start_exposure">DevCCDStartExposure</command>
        <command type="taco" taconame="id30/adsc/massif1" name="detector_reset">DevReset</command>
    """

    def __init__(self):
        pass

    @task
    def data_collection_hook(self, data_collect_parameters):
        self.dc_params = data_collect_parameters

    def _send_params(self, func, *args):
        for key, value in grouped(args, 2):
            func([key, str(value)])

    @task
    def prepare_acquisition(
        self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""
    ):
        self.oscil_start = start
        self.take_dark = take_dark
        self.osc_range = osc_range

        bx, by = self.get_beam_centre()

        self.execute_command("detector_state")
        # set Taco timeout to 15 seconds
        self.getCommandObject("detector_state").device.timeout(15)

        # set detector to Hardware Binned
        ccd_set_hwpar = self.getCommandObject("detector_sethwpar")
        self._send_params(
            ccd_set_hwpar, "adc", 1, "bin", 2, "save_raw", 0, "no_xform", 0
        )

        ccd_set_filepar = self.getCommandObject("detector_setfilepar")
        self._send_params(
            ccd_set_filepar,
            "filename",
            "%s/notset" % self.dc_params["fileinfo"]["directory"],
            "phi",
            start,
            "distance",
            self.dc_params["detectorDistance"],
            "wavelength",
            self.dc_params["wavelength"],
            "osc_range",
            osc_range,
            "time",
            exptime,
            "beam_x",
            bx,
            "beam_y",
            by,
            "comment",
            comment,
        )

    @task
    def set_detector_filenames(
        self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
    ):
        print "frame", frame_number, " - setting detector filename", filename, "phi=", start
        ccd_set_filepar = self.getCommandObject("detector_setfilepar")
        self._send_params(
            ccd_set_filepar,
            "filename",
            filename,
            "phi",
            start,
            "jpeg_name1",
            jpeg_full_path,
            "jpeg_size1",
            "1024x1024",
            "jpeg_size2",
            "250x250",
            "jpeg_name2",
            jpeg_thumbnail_full_path,
        )

    @task
    def start_acquisition(self, exptime, npass, first_frame):
        ccd_set_filepar = self.getCommandObject("detector_setfilepar")

        if first_frame and self.take_dark:  # self.dc_params.get("dark", 0):
            start = self.oscil_start
            dark_start = start - 2 * self.osc_range

            self.getObjectByRole("diffractometer").phiMotor.move(dark_start)

            logging.info("Taking 1st dark image")
            self._send_params(ccd_set_filepar, "kind", 0, "lastimage", 1)
            self.execute_command("detector_start_exposure")
            self.wait_detector(1)
            self.do_oscillation(
                dark_start,
                dark_start + self.osc_range,
                exptime,
                npass,
                save_diagnostic=False,
                operate_shutter=False,
            )
            self.execute_command("detector_stop")
            self.wait_detector(0)
            self.execute_command("detector_write_image")
            self.wait_detector(0)

            logging.info("Taking 2nd dark image")
            self._send_params(ccd_set_filepar, "kind", 1, "lastimage", 1)
            self.execute_command("detector_start_exposure")
            self.wait_detector(1)
            self.do_oscillation(
                dark_start + self.osc_range,
                start,
                exptime,
                npass,
                save_diagnostic=False,
                operate_shutter=False,
            )
            self.execute_command("detector_stop")
            self.wait_detector(0)
            self.execute_command("detector_write_image")
            self.wait_detector(0)

        self._send_params(ccd_set_filepar, "axis", 1, "kind", 5, "lastimage", 0)

        print "detector start exposure"
        self.execute_command("detector_start_exposure")
        self.wait_detector(1)

    @task
    def write_image(self, last_frame):
        if last_frame:
            ccd_set_filepar = self.getCommandObject("detector_setfilepar")
            self._send_params(ccd_set_filepar, "lastimage", 1)

        self.wait_detector(0)

        print "calling write_image"
        self.execute_command("detector_write_image")

    @task
    def stop_acquisition(self):
        print "calling stop"
        self.execute_command("detector_stop")

    @task
    def reset_detector(self):
        self.execute_command("detector_reset")

    def wait_detector(self, until_state):
        with gevent.Timeout(20, RuntimeError("Timeout waiting for detector")):
            state = self.execute_command("detector_state")
            print state, until_state
            while state != until_state:
                time.sleep(0.2)
                state = self.execute_command("detector_state")
                print "DET. WAITING FOR STATE ;", state, until_state
                if state in (-1, 3):
                    status = self.execute_command("detector_status")
                    raise RuntimeError(
                        "Detector problem: %s, hint: try to restart detector software"
                        % status
                    )

    @task
    def move_detector(self, detector_distance):
        pass  # self.bl_control.resolution.newDistance(detector_distance)

    @task
    def set_resolution(self, new_resolution):
        pass  # self.bl_control.resolution.move(new_resolution)

    def get_detector_distance(self):
        return (
            260
        )  # self.bl_control.resolution.res2dist(self.bl_control.resolution.getPosition()

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if osc_range < 1e-4:
            # still image
            return (start, start + osc_range)
        else:
            # prepare oscillation... what should we do?
            return (start, start + osc_range)

    @task
    def do_oscillation(
        self, start, end, exptime, npass=1, save_diagnostic=True, operate_shutter=True
    ):
        self.getObjectByRole("diffractometer").oscil(
            start, end, exptime, npass, save_diagnostic, operate_shutter
        )

    def open_fast_shutter(self):
        self.getObjectByRole("diffractometer").controller.fshut.open()

    def close_fast_shutter(self):
        self.getObjectByRole("diffractometer").controller.fshut.close()

    def get_flux(self):
        return -1

    def set_transmission(self, transmission_percent):
        pass

    def get_transmission(self):
        return 100

    def get_cryo_temperature(self):
        return 0

    @task
    def prepare_intensity_monitors(self):
        return

    def get_beam_centre(self):
        return (159.063, 163.695)
