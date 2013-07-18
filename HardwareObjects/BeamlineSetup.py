from HardwareRepository.BaseHardwareObjects import HardwareObject

class BeamlineSetup(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._object_by_path = {}


    def init(self):        
        self.transmission_hwobj = self.getObjectByRole('transmission')
        self.diffractometer_hwobj = self.getObjectByRole('diffractometer')
        self.sample_changer_hwobj = self.getObjectByRole('sample_changer')
        self.resolution_hwobj = self.getObjectByRole('resolution')
        
        self.shape_history_hwobj = self.getObjectByRole('shape_history')
        self.session_hwobj = self.getObjectByRole('session')        
        self.bl_config_hwobj = self.getObjectByRole('beamline_configuration')

        self.data_analysis_hwobj = self.getObjectByRole('data_analysis')
        self.workflow_hwobj = self.getObjectByRole('workflow')
        self.lims_client_hwobj = self.getObjectByRole('lims_client')
        self.collect_hwobj = self.getObjectByRole('collect')
        self.energy_hwobj = self.getObjectByRole('energy_scan')

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
            
        
