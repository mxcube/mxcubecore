"""
BeamlineConfiguration hardware object.

Contains static information about the beamline, and methods to retreive/handle
that information.
"""

import queue_model_objects_v1 as queue_model_objects
from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer

__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"


class BeamlineConfiguration(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)


    def detector_has_shutterless(self):
        """
        :returns: True if the detector is capable of shuterless.
        :rtype: bool
        """
        shutter_less = False
        
        try:
            shutter_less = self['detector'].getProperty('has_shutterless')

            if shutter_less is None:
                shutter_less = False

        except:
            shutter_less = False
            
        return shutter_less


    def tunable_wavelength(self):
        """
        :returns: Returns True if the beamline has tunable wavelength.
        :rtype: bool
        """
        tw = False
        
        try:
            tw = self.getProperty('tunable_wavelength')
            
            if tw is None:
                tw = False
                
        except:
            shutter_less = False
        
        return tw


    def get_default_acquisition_parameters(self):
        """
        :returns: A AcquisitionParameters object with all default parameters.
        """
        acq_parameters = queue_model_objects.AcquisitionParameters()
        
        acq_parameters.first_image = int(self["default_values"].\
                                         getProperty('start_image_number'))
        acq_parameters.num_images = int(self["default_values"].\
                                    getProperty('number_of_images'))
        acq_parameters.osc_start = round(float(self["default_values"].\
                                               getProperty('start_angle')), 2)
        acq_parameters.osc_range = round(float(self["default_values"].\
                                               getProperty('range')), 2)
        acq_parameters.overlap = round(float(self["default_values"].\
                                             getProperty('overlap')), 2)
        acq_parameters.exp_time = round(float(self["default_values"].\
                                              getProperty('exposure_time')), 4)
        acq_parameters.num_passes = int(self["default_values"].\
                                        getProperty('number_of_passes'))
        acq_parameters.energy = float()
        acq_parameters.resolution = float()
        acq_parameters.transmission = float()
        acq_parameters.inverse_beam = False
        acq_parameters.shutterless = bool(self['detector'].getProperty('has_shutterless'))
        acq_parameters.take_snapshots = True
        acq_parameters.take_dark_current = True
        acq_parameters.skip_existing_images = False

        acq_parameters.detector_mode = int(self["default_values"].\
                                           getProperty('detector_mode'))
        
        return acq_parameters

    def get_default_path_template(self):
        path_template = queue_model_objects.PathTemplate()

        path_template.directory = str()
        path_template.process_directory = str()
        path_template.base_prefix = str()
        path_template.mad_prefix = ''
        path_template.reference_image_prefix = ''
        path_template.wedge_prefix = ''
        path_template.template = str()
        path_template.run_number = self["default_values"].\
                                   getProperty('run_number')
        path_template.suffix = self["file_info"].getProperty('file_suffix')
        path_template.precision = '04'
        path_template.start_num = int(self["default_values"].\
                                      getProperty('start_image_number'))
        path_template.num_files = int(self["default_values"].\
                                      getProperty('number_of_images'))

        return path_template
