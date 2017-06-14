from HardwareRepository import HardwareRepository
import logging

import MiniDiff

import time
import calibrator
import scan_and_align
import sample_centring

class SOLEILMiniDiff(MiniDiff.MiniDiff):

    def init(self):
        MiniDiff.MiniDiff.init(self)
        
        self.phiDirection = self.getProperty("phi_direction")
        self.centeringPhiyDirection = -1
        self.calib_x = self.getChannelObject("calib_x")
        self.calib_y = self.getChannelObject("calib_y")
        self.beam_position_x = self.getChannelObject("beam_position_x")
        self.beam_position_y = self.getChannelObject("beam_position_y")
        self.chan_current_phase = self.getChannelObject('current_phase')
        self.chan_current_phase_index = self.getChannelObject('current_phase_index')
        self.chan_motor_positions = self.getChannelObject('motor_positions')
        self.chan_motor_states = self.getChannelObject('motor_states')
        self.chan_scan_number_of_passes = self.getChannelObject('scan_number_of_passes')
        self.chan_scan_range = self.getChannelObject('scan_range')
        self.chan_scan_exposure_time = self.getChannelObject('scan_exposure_time')
        self.chan_scan_start_angle = self.getChannelObject('scan_start_angle')
        self.chan_back_light_is_on = self.getChannelObject('back_light_is_on')
        self.chan_fast_shutter_is_open = self.getChannelObject('fast_shutter_is_open')
        self.chan_last_task_info = self.getChannelObject('last_task_info')
        
        self.cmd_get_motor_state = self.getCommandObject('getMotorState')
        self.cmd_start_set_phase = self.getCommandObject('startSetPhase')
        self.cmd_start_auto_focus = self.getCommandObject('startAutoFocus')
        self.cmd_start_scan = self.getCommandObject('startScan')
        
        self.collect_phase = 'DataCollection'
        self.beamlocate_phase = 'BeamLocation'
        self.transfer_phase = 'Transfer'
        self.centering_phase = 'Centring'
        
        try:
          phiz_ref = self["centringReferencePosition"].getProperty("phiz")
        except:
          phiz_ref = None
          
        self.centringPhiy=sample_centring.CentringMotor(self.phiyMotor, direction=self.centeringPhiyDirection)
        self.centringPhiz=sample_centring.CentringMotor(self.phizMotor, reference_position=phiz_ref)
        
        try:
            self.phase_list = eval(self.getProperty("phaseList"))
        except:
            self.phase_list = []
            
    def getCalibrationData(self, offset=None):
        return (1.0/self.calib_x.getValue(), 1.0/self.calib_y.getValue())

    def get_current_phase(self):
        """
        Descript. :
        """
        return self.chan_current_phase.getValue()
    
    def getBeamPosX(self):
        return self.beam_position_x.getValue()

    def getBeamPosY(self):
        return self.beam_position_y.getValue()
        
   
    def getPositions(self):
        return { "phi": float(self.phiMotor.getPosition()),
                 "focus": float(self.focusMotor.getPosition()),
                 "phiy": float(self.phiyMotor.getPosition()),
                 "phiz": float(self.phizMotor.getPosition()),
                 "sampx": float(self.sampleXMotor.getPosition()),
                 "sampy": float(self.sampleYMotor.getPosition()),
                 #"kappa": float(self.kappaMotor.getPosition()) if self.kappaMotor else None,
                 #"kappa_phi": float(self.kappaPhiMotor.getPosition()) if self.kappaPhiMotor else None,    
                 "zoom": float(self.zoomMotor.getPosition())}

    def moveMotors(self, roles_positions_dict):
        motor = { "phi": self.phiMotor,
                  "focus": self.focusMotor,
                  "phiy": self.phiyMotor,
                  "phiz": self.phizMotor,
                  "sampx": self.sampleXMotor,
                  "sampy": self.sampleYMotor,
                  #"kappa": self.kappaMotor,
                  #"kappa_phi": self.kappaPhiMotor,
                  "zoom": self.zoomMotor }
        
        for role, pos in roles_positions_dict.iteritems():
           m = motor.get(role)
           if not None in (m, pos):
             m.move(pos)
 
        # TODO: remove this sleep, the motors states should
        # be MOVING since the beginning (or READY if move is
        # already finished) 
        time.sleep(1)
        
        while not all([m.getState() == m.READY for m in motor.itervalues() if m is not None]):
           time.sleep(0.1)
    
    def _md2_state_tuple_to_name_value_list(item):
        name, value = item.split('=')
        return name, value
        
    def getState(self):
        motor_states = self.chan_motor_states.getValue()
        if all(['Ready' in state for state in motor_states]):
            return 'Ready'
        else:
            return 'Moving'
        
    def getOmegaState(self):
        return self.cmd_get_motor_state('Omega').name
        
    def getMotorState(self, motor_name):
        return self.cmd_get_motor_state(motor_name).name
        
    def get_phase_list(self):
        return self.phase_list

    def start_set_phase(self, name):
        """
        Descript. :
        """
        if self.cmd_start_set_phase is not None:
            self.cmd_start_set_phase(name)
        #self.refresh_video()

    def refresh_video(self):
        """
        Descript. :
        """
        if self.camera_hwobj is not None:
            if self.current_phase != "Unknown":  
                self.camera_hwobj.refresh_video()
        if self.beam_info_hwobj is not None: 
            self.beam_position = self.beam_info_hwobj.get_beam_position()         

    def start_auto_focus(self):
        """
        Descript. :
        """
        if self.cmd_start_auto_focus:
            self.cmd_start_auto_focus() 

    def sendGonioToCollect(self, oscrange, npass, exptime):
        diffstate = self.getState()
        logging.info("SOLEILCollect - setting gonio ready (state: %s)" % diffstate)

        self.chan_scan_number_of_passes.setValue(npass)
        self.chan_scan_range.setValue(oscrange)
        self.chan_scan_exposure_time.setValue(exptime)
        logging.info("SOLEILCollect - setting the collect phase position %s" % self.collect_phase)
        logging.info("SOLEILCollect - current phase %s" % self.get_current_phase())
        logging.info("SOLEILCollect - current phase index %s" % self.chan_current_phase_index.getValue())
        if self.get_current_phase() != self.collect_phase:
            logging.getLogger("user_level_log").info("Setting gonio to data collection phase.")
            self.start_set_phase(self.collect_phase)
        else:
            self.chan_back_light_is_on.setValue(False)
    
    def verifyGonioInCollect(self):
        while self.get_current_phase() != self.collect_phase:
            time.sleep(0.1)
        logging.getLogger("user_level_log").info("Capillary beamstop in the beam path, starting to collect.")   
    
    def goniometerReady(self):
        pass
    
    def wait(self):
        logging.info("MiniDiff wait" )
        while self.getState() == 'Moving':
            logging.info("MiniDiff waiting" )
            time.sleep(0.1)
    
    def setScanStartAngle(self, sangle):
        logging.info("MiniDiff / setting start angle to %s ", sangle )

        executed = False
        while executed is False:
            try:
                self.wait()
                logging.info("MiniDiff state %s " % self.getState())
                self.chan_scan_start_angle.setValue(sangle)
                #self.md2.write_attribute("ScanStartAngle", sangle )
                executed = True
            except Exception, e:
                print e
                logging.info('Problem writing ScanStartAngle command')
                logging.info('Exception ' + str(e))
    
    def startScan(self, wait=True):
        logging.info("MiniDiffPX2 / starting scan " )
        start = time.time()
        diffstate = self.getState()
        logging.info("SOLEILCollect - diffractometer scan started  (state: %s)" % diffstate)
            
        executed = False
        while executed is False:
            try:
                self.wait()
                self.cmd_start_scan()
                #self.md2.command_inout('startScan')
                #self.wait()
                executed = True
                logging.info('Successfully executing StartScan command')
            except Exception, e:
                executed = False
                print e
                os.system('echo $(date) error executing StartScan command >> /927bis/ccd/collectErrors.log')
                logging.info('Problem executing StartScan command')
                logging.info('Exception ' + str(e))
                
        
        while self.chan_fast_shutter_is_open.getValue() is False and self.chan_last_task_info.getValue()[3] == 'null':
            logging.info('Successfully executing StartScan command, waiting for fast shutter to open or scan to finish')
            time.sleep(0.05)
        
        while self.chan_fast_shutter_is_open.getValue() is True and self.chan_last_task_info.getValue()[3] == 'null':
            logging.info('Successfully executing StartScan command, waiting for fast shutter to close or scan to finish')
            time.sleep(0.05)

        logging.info("MiniDiff Scan took %s seconds "  % str(time.time() - start))
        return
    
    
    def beamPositionCheck(self):
        logging.getLogger("HWR").info("Going to check the beam position at all zooms")
        logging.getLogger("user_level_log").info("Starting beam position check for all zooms")
        gevent.spawn(self.bpc)
    
    def bpc(self):
        calib = calibrator.calibrator(fresh=True, save=True)
        logging.getLogger("user_level_log").info("Adjusting camera exposure time for visualisation on the scintillator")
        calib.prepare()
        logging.getLogger("user_level_log").info("Calculating beam position for individual zooms")
        for zoom in calib.zooms:
            logging.getLogger("user_level_log").info("Zoom %s" % zoom)
            calibrator.main(calib, zoom)
            
        logging.getLogger("user_level_log").info("Saving results into database")
        calib.updateMD2BeamPositions()
        logging.getLogger("user_level_log").info("Setting camera exposure time back to 0.050 seconds")
        calib.tidy()
        diff = calib.get_difference_zoom_10()
        logging.getLogger("user_level_log").info("The beam moved %s um horizontally and %s um vertically since the last calibration" % (str(round(diff[0],1)), str(round(diff[1],1))) )
        
        calib.saveSnap()
        
        logging.getLogger("user_level_log").info("Beam position check finished")
        
    def apertureAlign(self):
        logging.getLogger("HWR").info("Going to realign the current aperture")
        logging.getLogger("user_level_log").info("Aligning the current aperture")
        gevent.spawn(self.aa)
        
    def aa(self):
        logging.getLogger("user_level_log").info("Adjusting camera exposure time for visualisation on the scintillator")
        a = scan_and_align.scan_and_align('aperture', display=False)
        logging.getLogger("user_level_log").info("Scanning the aperture")
        a.scan()
        a.align(optimum='com')
        a.save_scan()
        logging.getLogger("user_level_log").info("Setting camera exposure time back to 0.050 seconds")
        logging.getLogger("user_level_log").info("Aligning aperture finished")
        a.predict()

        
def test():
    import os
    import time
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    minidiff = hwr.getHardwareObject("/soleil-minidiff")
    print 'SOLEILMiniDiff self.sampleXMotor', minidiff.sampleXMotor, minidiff.sampleXMotor.getRealPosition()
    print 'sendGonioToCollect', minidiff.sendGonioToCollect(0.5, 1, 0.5)
    print 'current phase', minidiff.get_current_phase()
    print "phi.getPosition", minidiff.phiMotor.getPosition(), minidiff.phiMotor.getRealPosition()
    print "SampXMotor", minidiff.sampleXMotor.getPosition()
    print "getCalibrationData", minidiff.getCalibrationData()
    print "SOLEILMiniDiff phiDirection", minidiff.phiDirection
    print "SOLEILMiniDiff getPositions", minidiff.getPositions()

if __name__ == '__main__':
    test()
