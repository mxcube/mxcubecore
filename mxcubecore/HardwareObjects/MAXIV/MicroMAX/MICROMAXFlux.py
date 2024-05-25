from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux
from mxcubecore import HardwareRepository as HWR
import numpy as np
import logging
import time
import gevent
import tango


class MICROMAXFlux(AbstractFlux):

    def __init__(self, name):

        AbstractFlux.__init__(self, name)

        self.al_coeff = [2.70033918627e-07, -2.98687890398e-05,
                         0.00123604226164, -0.0258445478508,
                         0.443366527092, -1.88717819273,
                         6.51896436249, -8.15712686311]

        self.sipha_coeff = [5.6946e-08,  -7.20953e-06,
                            0.000359681, -0.00844784,
                            0.242434, -0.960961,
                            4.52577, -7.00435]

        self.air_coeff = [-4.93236e-03,  6.84953e-01,
                          -35.9648, 845.516,
                          -8440.87, 66209.7,
                          -225579, 309746]

        self.al_model = np.array(self.al_coeff)
        self.sipha_model = np.array(self.sipha_coeff)
        self.air_model = np.array(self.air_coeff)

        self.e = 1.6022e-16
        self.al_thickness = 1632 # um
        self.airsample_length = 0
        self.detdiode_length = 45.

        self.detector_hwobj = None
        self.detector_distance_hwobj = None
        self.energy_hwobj = None

        self.air_length = None
        self.energy = None
        self.shutter_hwobj = None
        self.shutter_state = None
        self.timeout = 10

        self.current_flux = 0.0
        self.flux_density = -1.0
        self.flux_density_energy = 0.0
        self.channel_value = 0.0

        self.opt_diode = {}
        self.diode = {}
        self.det_mot = {}

    def init(self):
        self.logger = logging.getLogger("HWR")
        
        self.energy_hwobj = self.get_object_by_role('energy')
        self.detector_hwobj = HWR.beamline.detector
        self.diffractometer_hwobj = HWR.beamline.diffractometer
        self.beam_info_hwobj = self.get_object_by_role("beam_info")
        self.energy_mot = tango.DeviceProxy('pseudomotor/mono_energy_ctrl/1')
        self.opt_diode["ch1"] = tango.DeviceProxy("expchan/albaem_ctrl_02/2")
        self.opt_diode["ch2"] = tango.DeviceProxy("expchan/albaem_ctrl_02/3")
        self.opt_diode["ch3"] = tango.DeviceProxy("expchan/albaem_ctrl_02/4")
        self.opt_diode["ch4"] = tango.DeviceProxy("expchan/albaem_ctrl_02/5")
        self.diode["jungfrau"] = tango.DeviceProxy("expchan/albaem_ctrl_04/3")
        self.det_mot["jungfrau"] = tango.DeviceProxy("b312a-e06/dia/tabled-01-zo")
        self.diode["eiger"] = tango.DeviceProxy("expchan/albaem_ctrl_04/2")
        self.det_mot["eiger"] = tango.DeviceProxy("b312a-e06/dia/tabled-01-zi")

             
    def get_flux(self):
        return self.current_flux

    def get_instant_flux(self):

        # get_instant_flux
        try:
            self.current_flux = self._get_instant_flux()
        except Exception as ex:
            self.logger.error("ERROR acquiring! %s", str(ex))

        try:
            self.diffractometer_hwobj.close_fast_shutter()
            self.logger.info("Fast shutter closed!")
        except Exception as ex:
            self.logger.error("Cannot close fast shutter! %s", str(ex))


    def wait_safety_shutter_open(self):
        with gevent.Timeout(10, RuntimeError('Timeout waiting for safety shutter open')):
            while self.shutter_hwobj.readShutterState() != 'opened':
                gevent.sleep(0.2)

    def wait_fast_shutter_open(self, timeout=5):
        with gevent.Timeout(timeout, RuntimeError('Timeout waiting for safety shutter open')):
            while not self.diffractometer_hwobj.is_fast_shutter_open():
                gevent.sleep(0.2)

    def transmit(self, length, energy, model):
        att_l = model[0] * energy**7 + model[1] * energy**6 \
            + model[2] * energy**5 + model[3] * energy**4 \
            + model[4] * energy**3 + model[5] * energy**2 \
            + model[6] * energy + model[7]
        transmission = np.exp(-length / att_l)
        return transmission

    def _calc_flux(self, energy, dist, current):
        spectra_resp_factor = (0.1487-0.1896)/(14400-12500)
        spectra_resp = (energy - 12500) * spectra_resp_factor + 0.1896
        flux = current / spectra_resp / (1.6e-19 * energy)
        air_transmission = self.transmit(dist * 1000.0, energy / 1000.0, self.air_coeff)
        al_transmission = self.transmit(self.al_thickness, energy / 1000.0, self.al_coeff)
        print("Air transmission is {} al_transmission is {}".format(air_transmission, al_transmission))
        full_flux = flux / air_transmission
        return full_flux


    def calc_flux(self):
        """
        det can be "jungfrau" or "eiger"
        """
        energy_ev = self.energy_hwobj.get_current_energy() * 1000.0
        tmp = self.detector_hwobj.get_property("model")
        det = tmp.lower()
        det_dist = self.det_mot[det].Position
        current = self.diode[det].InstantCurrent
        """
        energy_ev = 12500
        current = 6.70E-04
        det_dist = 900
        """
        flux = self._calc_flux(energy_ev, det_dist, current)
        print("Current on the detector photodiode is {}".format(current))
        return flux

    def check_beam_opt(self):
        energy_ev = self.energy_hwobj.get_current_energy() *1000.0
        msg = ""
        total = 0.0
        for i in range(1,5):
            ch_id = "ch{}".format(i)
            current = self.opt_diode[ch_id].InstantCurrent
            msg += " {} {},".format(ch_id, current)
            total+= current
        flux = total * ( -0.534515 * energy_ev * energy_ev * energy_ev * energy_ev - \
               43197.6 * energy_ev * energy_ev * energy_ev + 5.13449e+09 * energy_ev * energy_ev \
               - 4.39169e+13 * energy_ev + 1.14591e+17)
        final_msg = "The currents on b312a-o06-ctl-aemhv-01 are {} sum value is {}".format(msg, total)
        print(final_msg)
        print("Estimated flux is {:.2e} ph/s".format(flux))
        return final_msg, flux

