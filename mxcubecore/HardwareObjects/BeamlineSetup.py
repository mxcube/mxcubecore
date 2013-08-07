__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"

from HardwareRepository.BaseHardwareObjects import HardwareObject


class BeamlineSetup(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._object_by_path = {}
        self._role_list = ['transmission', 'diffractometer', 'sample_changer',
                           'resolution', 'shape_history', 'session',
                           'beamline_configuration', 'data_analysis',
                           'workflow', 'lims_client', 'collect', 'energy']


    def init(self):        
        for role in self._role_list:
            self.get_object_by_role(role)

        

        self._object_by_path['/beamline/energy'] = self.energy_hwobj
        self._object_by_path['/beamline/resolution'] = self.resolution_hwobj
        self._object_by_path['/beamline/transmission'] = self.transmission_hwobj


    def get_object_by_role(self, role):
        try:
            value = self.getObjectByRole(role)            
        except:
            value = None
            logging.getLogger('HWR').exception('Could not get object with role: ' + \
                                               role + 'from hardware repository.')
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
        hwobj = None

        try:
            hwobj = self._object_by_path[path]
        except KeyError:
            raise ArgumentException('Invalid path')

        return hwobj.get_value()
