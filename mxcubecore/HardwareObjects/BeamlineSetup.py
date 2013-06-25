from HardwareRepository.BaseHardwareObjects import HardwareObject

class BeamlineSetup(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._object_by_path = {}


    def init(self):
        self.diffractometer_hwobj = self.getObjectByRole('diffractometer')
        self.shape_history_hwobj = self.getObjectByRole('shape_history')
        self.energy_hwobj = self.getObjectByRole('energy_scan')
        self.transmission_hwobj = self.getObjectByRole('transmission')
        self.resolution_hwobj = self.getObjectByRole('resolution')                
        self.session_hwobj = self.getObjectByRole('session')        
        self.workflow_hwobj = self.getObjectByRole('workflow')


        self._object_by_path['/beamline/energy'] = self.energy_hwobj
        self._object_by_path['/beamline/resolution'] = self.resolution_hwobj
        self._object_by_path['/beamline/transmission'] = self.transmission_hwobj


    def read_value(self, path):
        hwobj = None

        try:
            hwobj = self._object_by_path[path]
        except KeyError:
            raise ArgumentException('Invalid path')

        return hwobj.get_value()
            
        
