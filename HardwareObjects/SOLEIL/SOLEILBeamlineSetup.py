import os
import logging
import jsonpickle
import queue_model_objects_v1 as queue_model_objects

from HardwareRepository.BaseHardwareObjects import HardwareObject
from XSDataMXCuBEv1_3 import XSDataInputMXCuBE
import queue_model_enumerables_v1 as queue_model_enumerables

from HardwareRepository.HardwareRepository import HardwareRepository
from BeamlineSetup import BeamlineSetup

class SOLEILBeamlineSetup(BeamlineSetup):
    
    def __init__(self):
        BeamlineSetup.__init__(self, name)
    
    def get_default_char_acq_parameters(self):
        """
        :returns: A AcquisitionParameters object with all default parameters.
        """
        acq_parameters = queue_model_objects.AcquisitionParameters()
        parent_key = "default_characterisation_values"

        img_start_num = self[parent_key].getProperty('start_image_number')
        num_images = self[parent_key].getProperty('number_of_images')
        num_wedges = self[parent_key].getProperty('number_of_wedges')
        osc_range = round(float(self[parent_key].getProperty('range')), 2)
        overlap = round(float(self[parent_key].getProperty('overlap')), 2)
        exp_time = round(float(self[parent_key].getProperty('exposure_time')), 4)
        num_passes = int(self[parent_key].getProperty('number_of_passes'))
        wedge_size = int(self[parent_key].getProperty('wedge_size'))
        shutterless = self.detector_has_shutterless()
        
        try:
            detector_mode = self.detector_hwobj.default_mode() 
        except AttributeError:
            detector_mode = None

        acq_parameters.first_image = int(img_start_num)
        acq_parameters.num_images = int(num_images)
        acq_parameters.osc_start = self._get_omega_axis_position()
        acq_parameters.osc_range = osc_range
        acq_parameters.num_wedges = num_wedges
        acq_parameters.wedge_size = wedge_size
        acq_parameters.kappa = self._get_kappa_axis_position()
        acq_parameters.kappa_phi = self._get_kappa_phi_axis_position()
        acq_parameters.overlap = overlap
        acq_parameters.exp_time = exp_time
        acq_parameters.num_passes = num_passes
        acq_parameters.resolution = self._get_resolution()
        acq_parameters.energy = self._get_energy()
        acq_parameters.transmission = self._get_transmission()

        acq_parameters.shutterless = self._has_shutterless()
        acq_parameters.detector_mode = self._get_roi_modes()

        acq_parameters.inverse_beam = False
        acq_parameters.take_dark_current = True
        acq_parameters.skip_existing_images = False
        acq_parameters.take_snapshots = True

        return acq_parameters