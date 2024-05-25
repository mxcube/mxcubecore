from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux
from mxcubecore import HardwareRepository as HWR
import numpy as np
import logging
import time
import gevent



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
        self.al_length = 1
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
        self.ori_motors = None
        self.ori_phase = None

        self.current_flux = 0.0
        self.flux_density = -1.0
        self.flux_density_energy = 0.0
        self.channel_value = 0.0
        self.check_beam_result = False
        self.flux_aem = None
        self.flux_aem_dev = None

    def init(self):
        self.logger = logging.getLogger("HWR")
        
        self.cmd_macro = self.getCommandObject('calculate_flux_mxcube')
        self.cmd_macro.connectSignal('macroResultUpdated', self.macro_finished)

        self.check_beam_macro = self.getCommandObject('checkbeam')
        # is the following really needed? mmm...
        self.check_beam_macro.connectSignal('macroResultUpdated', self.macro_finished)
        self.energy_hwobj = self.getObjectByRole('energy')
        self.connect(self.energy_hwobj, "energyChanged", \
             self.energy_changed)
        self.detector_hwobj = HWR.beamline.detector
        self.detector_distance_hwobj = HWR.beamline.detector.distance
        self.detector_cover_hwobj = self.getObjectByRole("detector_cover")
        self.diffractometer_hwobj = HWR.beamline.diffractometer_hwobj
        self.beam_info_hwobj = self.getObjectByRole("beam_info")

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
        """
        calculate the current flux, complete version
         1. Close fast shutter
         4. Set MD3 phase and beamstop and motor positions
         5. Ensure detector cover is closed
         6. Measure flux value (sardana macro call and some math)
         7. Put MD3 back to normal position
        """

        try:
            self.diffractometer_hwobj.close_fast_shutter()
            self.logger.info("Fast shutter closed!")
        except Exception as ex:
            self.logger.error("Cannot close fast shutter! %s", str(ex))
            return

        # set MD3 phase
        try:
            self.ori_motors, self.ori_phase = self.diffractometer_hwobj.set_calculate_flux_phase()
        except Exception as ex:
            self.logger.error("Cannot set MD3 phase for flux calculatio! %s", str(ex))
            return

        # check detector cover is closed
        try:
            if self.detector_cover_hwobj.readShutterState() == 'opened':
                logging.getLogger("HWR").info("Closing the detector cover")
                self.detector_cover_hwobj.closeShutter()
        except:
            logging.getLogger("HWR").exception("Could not close the detector cover")
            return

        # get_instant_flux
        try:
            self.current_flux = self.get_instant_flux()
        except Exception as ex:
            self.logger.error("ERROR acquiring! %s", str(ex))

        try:
            self.diffractometer_hwobj.close_fast_shutter()
            self.logger.info("Fast shutter closed!")
        except Exception as ex:
            self.logger.error("Cannot close fast shutter! %s", str(ex))

        self.diffractometer_hwobj.finish_calculate_flux(self.ori_motors, self.ori_phase)

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
        print("Air transmission is {}".format(air_transmission))
        full_flux = flux / air_transmission
        return full_flux


    def _get_instant_flux(self, scale=1.0, adjust_atten = 1):
        """
        calculate the current flux, a simpler and faster version
         - assuming safety shutter is open
         - no check of beam stability   
        """
        energy = self.energy_hwobj.getCurrentEnergy()

        self.logger.info("Start to measure flux")
        try:
            # measure dark current, no need to adjust attenuation
            self.acquire(adjust_atten = 0)
            current_offset = self.channel_value
        except Exception as ex:
            self.logger.error("ERROR reading offset! %s", str(ex))
            return -101

        self.logger.info("Current Offset: {}".format(current_offset))

        try:
            self.diffractometer_hwobj.open_fast_shutter()
            self.wait_fast_shutter_open()
            self.logger.info("Fast shutter opened!")
        except Exception as ex:
            self.logger.error("Cannot open fast shutter! %s", str(ex))
            return -102

        time.sleep(2)

        try:
            self.acquire(adjust_atten = adjust_atten)
        except Exception as ex:
            self.logger.error("ERROR Acquiring! %s", str(ex))
            self.diffractometer_hwobj.close_fast_shutter()
            return -103
        self.diffractometer_hwobj.close_fast_shutter()
        current_meas = self.channel_value
        self.logger.info("Current Measurement: {}".format(current_meas))

        current = current_meas - current_offset

        air_length = self.detector_distance_hwobj.getPosition() * 1000 + \
            self.airsample_length
        total_transmission = self.transmit(self.al_length, energy, self.al_model) *\
            self.transmit(air_length, energy, self.air_model)

        sipha_absorp = 1 - self.transmit(self.detdiode_length, energy, self.sipha_model)

        flux = self.si_diode_flux(current, total_transmission, sipha_absorp, energy)

        if flux < 0: flux = 0
        # multiply the flux value by 1000 due to some issue with AlbaEM
        flux = flux * 1000 * scale
        if flux < 50000000:
            flux = 0
        self.current_flux = "{:.2E}".format(flux)
        self.flux_value_changed()
        self.logger.info("Flux Measurement: {}".format(flux))
        return flux
