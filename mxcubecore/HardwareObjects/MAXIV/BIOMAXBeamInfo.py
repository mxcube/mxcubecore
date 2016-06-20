import logging
from HardwareRepository import HardwareRepository
import BeamInfo

class BIOMAXBeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)

    def init(self): 
        self.chan_beam_size_microns = None 
        self.chan_beam_shape_ellipse = None 
        BeamInfo.BeamInfo.init(self)
        
        self.camera = self.getDeviceByRole('camera')
        self.chan_beam_pos_x = self.addChannel({"type":"exporter", "name":"BeamPositionHorizontal"  }, 'BeamPositionHorizontal')
        self.chan_beam_pos_y = self.addChannel({"type":"exporter", "name":"BeamPositionVertical"  }, 'BeamPositionVertical')
        self.chan_beam_size_x = self.addChannel({"type":"exporter", "name":"BeamSizeHorizontal"  }, 'BeamSizeHorizontal')
        self.chan_beam_size_y = self.addChannel({"type":"exporter", "name":"BeamSizeVertical"  }, 'BeamSizeVertical') 
        self.chan_beam_shape_ellipse = self.addChannel({"type":"exporter", "name":"BeamShapeEllipse"  }, 'BeamShapeEllipse')
        self.chan_ImageZoom=self.addChannel({"type":"exporter", "name":"ImageZoom"  }, 'ImageZoom')



        print "beam x %s and y %s " % (self.chan_beam_pos_x.getValue(),self.chan_beam_pos_y.getValue())

        if self.chan_beam_pos_x is not None and self.chan_beam_pos_y is not None:
            #self.get_beam_position()
            self.connect(self.chan_beam_pos_x, "beamPosChanged",self.get_beam_position)
            self.connect(self.chan_beam_pos_y, "beamPosChanged",self.get_beam_position)
            #self.emit("beamInfoChanged", (self.beam_info_dict, )

       
        if self.chan_beam_size_x is not None and self.chan_beam_size_y is not None:
            #self.get_beam_size()
            self.connect(self.chan_beam_size_x, "beamInfoChanged",self.get_beam_size)
            self.connect(self.chan_beam_size_y, "beamInfoChanged",self.get_beam_size)


#        self.get_beam_size()
#        self.beam_size_aperture=self.aperture_hwobj.getApertureSize()
        self.aperture_pos_changed(self.aperture_hwobj.getApertureSize())
	self.emit("beamInfoChanged", (self.beam_info_dict, ))
        self.emit("beamPosChanged", (self.beam_position, ))

    def get_beam_position(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        logging.info ("camera is %s", str(self.camera))
        try:
            zoom = self.chan_ImageZoom.getValue()
            self.beam_position[0] = self.chan_beam_pos_x.getValue() * zoom
            self.beam_position[1] = self.chan_beam_pos_y.getValue() * zoom
        except:
            self.beam_position[0] = self.camera.getWidth() / 2
            self.beam_position[1] = self.camera.getHeight() / 2
        return self.beam_position


    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self,*args):
        BeamInfo.BeamInfo.evaluate_beam_info(self,*args)
        try:
            if self.chan_beam_shape_ellipse.getValue():
                self.self.beam_info_dict["shape"] = "ellipse"
            else:
                self.beam_info_dict["shape"] = "circular"
        except:    
                self.beam_info_dict["shape"] = "circular"#"ellipse"
        curpos=self.aperture_hwobj.getCurrentPositionName()
        size_x = size_y = eval(str(curpos)) / 1000.0
        self.beam_info_dict["size_x"] = size_x
        self.beam_info_dict["size_y"] = size_y
        return self.beam_info_dict
