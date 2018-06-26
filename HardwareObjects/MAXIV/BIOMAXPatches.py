from HardwareRepository.BaseHardwareObjects import HardwareObject
import types
import logging
import gevent

class BIOMAXPatches(HardwareObject):
    '''
    Hwobj for patching hwobj methods without inheriting classes.
    '''
    def before_load_sample(self):
        '''
        Ensure that the detector is in safe position and sample changer in SOAK
        '''
	if not self.sample_changer._chnPowered.getValue():
	    raise RuntimeError('Cannot load sample, sample changer not powered')
	if not self.sc_in_soak():
	    raise RuntimeError('Cannot load sample, sample changer not in SOAK position')
	self.curr_dtox_pos = self.dtox_hwobj.getPosition()
        if self.dtox_hwobj is not None and self.dtox_hwobj.getPosition() < self.safe_position:
            logging.getLogger("HWR").info("Moving detector to safe position before loading a sample.")
            logging.getLogger("user_level_log").info("Moving detector to safe position before loading a sample.")
	    self.wait_motor_ready(self.dtox_hwobj)
            self.dtox_hwobj.syncMove(self.safe_position, timeout = 30)
            logging.getLogger("HWR").info("Detector in safe position, position: %s" %self.dtox_hwobj.getPosition())
            logging.getLogger("user_level_log").info("Detector in safe position, position: %s" %self.dtox_hwobj.getPosition())
        else:
            logging.getLogger("HWR").info("Detector already in safe position.")
            logging.getLogger("user_level_log").info("Detector already in safe position.")
	

    def after_load_sample(self):
        '''
        Move to centring after loading the sample
        '''
        if self.diffractometer is not None and self.diffractometer.get_current_phase() != 'Centring':
            logging.getLogger("HWR").info("Changing diffractometer phase to Centring")
            logging.getLogger("user_level_log").info("Changing diffractometer phase to Centring")
            try:
                self.diffractometer.wait_device_ready(15)
            except:
                pass
            self.diffractometer.set_phase('Centring')
            logging.getLogger("HWR").info("Diffractometer phase changed, current phase: %s" %self.diffractometer.get_current_phase())
        else:
            logging.getLogger("HWR").info("Diffractometer already in Centring")
            logging.getLogger("user_level_log").info("Diffractometer already in Centring")
        logging.getLogger("HWR").info("Moving detector to pre-mount position %s" %self.curr_dtox_pos)
        self.dtox_hwobj.syncMove(self.curr_dtox_pos, timeout = 30)
 

    def new_load(self, *args, **kwargs):
        logging.getLogger("HWR").info("Sample changer in SOAK position: %s" %self.sc_in_soak())
        self.before_load_sample()
        self.__load(args[1])
        self.after_load_sample()

    def new_unload(self, *args, **kwargs):
        logging.getLogger("HWR").info("Sample changer in SOAK position: %s" %self.sc_in_soak())
        self.before_load_sample()
        self.__unload(args[1])
        #self.after_load_sample()

    def wait_motor_ready(self, mot_hwobj, timeout=30):
	with gevent.Timeout(timeout, RuntimeError('Motor not ready')):
	    while mot_hwobj.is_moving():
	        gevent.sleep(0.5)

    def sc_in_soak(self):
	return self.sample_changer._chnInSoak.getValue()

    '''
    def sc_in_soak(self):
	x_pos = self.sample_changer.getChannelObject('Xpos').getValue()
	y_pos = self.sample_changer.getChannelObject('Ypos').getValue()
	z_pos = self.sample_changer.getChannelObject('Zpos').getValue()
	rx_pos = self.sample_changer.getChannelObject('RXpos').getValue()
	ry_pos = self.sample_changer.getChannelObject('RYpos').getValue()
	rz_pos = self.sample_changer.getChannelObject('RZpos').getValue()
	sc = self.sample_changer

	x_in_soak = sc.xpos_soak - 1 < x_pos < sc.xpos_soak + 1
	y_in_soak = sc.ypos_soak - 1 < y_pos < sc.ypos_soak + 1
	y_in_soak = sc.zpos_soak - 1 < z_pos < sc.zpos_soak + 1
	rx_in_soak = sc.rxpos_soak - 1 < rx_pos < sc.rxpos_soak + 1
	ry_in_soak = sc.rypos_soak - 1 < ry_pos < sc.rypos_soak + 1
	rz_in_soak = sc.rzpos_soak - 1 < rz_pos < sc.rzpos_soak + 1

	return x_in_soak & y_in_soak & y_in_soak & rx_in_soak & ry_in_soak & rz_in_soak
    '''
    def init(self, *args):
        self.sample_changer = self.getObjectByRole('sample_changer')
        self.diffractometer = self.getObjectByRole('diffractometer')
        self.__load = self.sample_changer.load
        self.__unload = self.sample_changer.unload
	self.curr_dtox_pos = None
        self.dtox_hwobj = self.getObjectByRole('dtox')
        #self.sample_changer.load = types.MethodType(self.new_load, self.sample_changer)
        #self.sample_changer.unload = types.MethodType(self.new_unload, self.sample_changer)
	'''
        position_attrs = ('Xpos', 'Ypos', 'Zpos', 'RXpos', 'RYpos', 'RZpos')
	for channel_name in position_attrs:
	    self.sample_changer.addChannel({"type": "tango",
                             "name": channel_name,
                             "tangoname": self.sample_changer.tangoname,
                             "timeout": 2000,
                             },
                            channel_name
                            )
	'''
        self.sample_changer.load = types.MethodType(self.new_load, self.sample_changer)
        self.sample_changer.unload = types.MethodType(self.new_unload, self.sample_changer)
