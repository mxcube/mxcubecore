import logging
import jsonpickle

import queue_model_objects_v1 as queue_model_objects
from HardwareRepository.BaseHardwareObjects import HardwareObject

__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"


class BeamlineSetup(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._object_by_path = {}
        self._role_list = ['transmission', 'diffractometer', 'sample_changer',
                           'resolution', 'shape_history', 'session',
                           'data_analysis', 'workflow', 'lims_client',
                           'collect', 'energy']

    def init(self):
        """
        Framework 2 init, inherited from HardwareObject.
        """
        for role in self._role_list:
            self._get_object_by_role(role)

        self._object_by_path['/beamline/energy'] = self.energy_hwobj
        self._object_by_path['/beamline/resolution'] = self.resolution_hwobj
        self._object_by_path['/beamline/transmission'] =\
            self.transmission_hwobj

    def _get_object_by_role(self, role):
        """
        Gets the object with the role <role>' and adds the attribute
        <role>_hwobj to the current instance.
        """
        try:
            value = self.getObjectByRole(role)
        except:
            value = None
            logging.getLogger('HWR').exception('Could not get object with ' +\
                'role:' + role + 'from hardware repository.')

        setattr(self, role + '_hwobj', value)

    def read_value(self, path):
        """
        Reads the value of the hardware object at the given path. The
        hardware object must have the get_value method.

        :param path: Path to a hardware object.
        :type path: str

        :returns: The 'value' of the hardware object.
        :rtype: Return type of get_value of the hardware object.
        """
        value = None

        if path == '/beamline/default-acquisition-parameters/':
            value = jsonpickle.encode(self.get_default_acquisition_parameters())
        elif path == '/beamline/default-path-template/':
            value = jsonpickle.encode(self.get_default_path_template())
        else:
            hwobj = None

            try:
                hwobj = self._object_by_path[path]
                value = hwobj.get_value()
            except KeyError:
                raise KeyError('Invalid path')

        return value

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
            tw = False

        return tw

    def disable_num_passes(self):
        """
        :returns: Returns True if it is possible to use the number of passes
                  collection parameter.
        :rtype: bool
        """
        disable_num_passes = False

        try:
            disable_num_passes = self.getProperty('disable_num_passes')

            if disable_num_passes is None:
                disable_num_passes = False

        except:
            disable_num_passes = False

        return disable_num_passes

    def get_default_characterisation_parameters(self):
        """
        :returns: A AcquisitionParameters object with all default parameters.
        """
        acq_parameters = queue_model_objects.AcquisitionParameters()
        parent_key = "default_characterisation_values"

        acq_parameters.first_image = int(self[parent_key].\
                                             getProperty('start_image_number'))
        acq_parameters.num_images = int(self[parent_key].\
                                    getProperty('number_of_images'))
        acq_parameters.osc_start = round(float(self[parent_key].\
                                               getProperty('start_angle')), 2)
        acq_parameters.osc_range = round(float(self[parent_key].\
                                               getProperty('range')), 2)
        acq_parameters.overlap = round(float(self[parent_key].\
                                             getProperty('overlap')), 2)
        acq_parameters.exp_time = round(float(self[parent_key].\
                                              getProperty('exposure_time')), 4)
        acq_parameters.num_passes = int(self[parent_key].\
                                        getProperty('number_of_passes'))
        acq_parameters.energy = float()
        acq_parameters.resolution = float()
        acq_parameters.transmission = float()
        acq_parameters.inverse_beam = False
        acq_parameters.shutterless = bool(self['detector'].\
                                          getProperty('has_shutterless'))
        acq_parameters.take_snapshots = True
        acq_parameters.take_dark_current = True
        acq_parameters.skip_existing_images = False

        acq_parameters.detector_mode = int(self[parent_key].\
                                           getProperty('detector_mode'))

        return acq_parameters

    def get_default_acquisition_parameters(self):
        """
        :returns: A AcquisitionParameters object with all default parameters.
        """
        acq_parameters = queue_model_objects.AcquisitionParameters()
        parent_key = "default_acquisition_values"


        acq_parameters.first_image = int(self[parent_key].\
                                         getProperty('start_image_number'))
        acq_parameters.num_images = int(self[parent_key].\
                                    getProperty('number_of_images'))
        acq_parameters.osc_start = round(float(self[parent_key].\
                                               getProperty('start_angle')), 2)
        acq_parameters.osc_range = round(float(self[parent_key].\
                                               getProperty('range')), 2)
        acq_parameters.overlap = round(float(self[parent_key].\
                                             getProperty('overlap')), 2)
        acq_parameters.exp_time = round(float(self[parent_key].\
                                              getProperty('exposure_time')), 4)
        acq_parameters.num_passes = int(self[parent_key].\
                                        getProperty('number_of_passes'))
        acq_parameters.energy = float()
        acq_parameters.resolution = float()
        acq_parameters.transmission = float()
        acq_parameters.inverse_beam = False
        acq_parameters.shutterless = bool(self['detector'].\
                                          getProperty('has_shutterless'))
        acq_parameters.take_snapshots = True
        acq_parameters.take_dark_current = True
        acq_parameters.skip_existing_images = False

        acq_parameters.detector_mode = int(self[parent_key].\
                                           getProperty('detector_mode'))

        return acq_parameters

    def get_default_path_template(self):
        """
        :returns: A PathTemplate object with default parameters.
        """
        path_template = queue_model_objects.PathTemplate()
        parent_key = "default_acquisition_values"

        path_template.directory = str()
        path_template.process_directory = str()
        path_template.base_prefix = str()
        path_template.mad_prefix = ''
        path_template.reference_image_prefix = ''
        path_template.wedge_prefix = ''
        path_template.run_number = self[parent_key].\
                                   getProperty('run_number')
        path_template.suffix = self.session_hwobj["file_info"].\
                               getProperty('file_suffix')
        path_template.precision = '04'
        path_template.start_num = int(self[parent_key].\
                                      getProperty('start_image_number'))
        path_template.num_files = int(self[parent_key].\
                                      getProperty('number_of_images'))

        return path_template
