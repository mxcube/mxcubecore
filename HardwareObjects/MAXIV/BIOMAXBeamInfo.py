import logging
from HardwareRepository import HardwareRepository
import BeamInfo
import gevent
import time
import copy
class BIOMAXBeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)

    def init(self): 
        self.chan_beam_size_microns = None 
        self.chan_beam_shape_ellipse = None 
        #self.keep_polling = True
        BeamInfo.BeamInfo.init(self)
        
        self.camera = self.getDeviceByRole('camera')
        self.chan_beam_pos_x = self.getChannelObject("BeamPositionHorizontal")
        self.chan_beam_pos_y = self.getChannelObject("BeamPositionVertical")
        self.chan_beam_size_x = self.getChannelObject("BeamSizeHorizontal")
        self.chan_beam_size_y = self.getChannelObject("BeamSizeVertical")
        self.chan_beam_shape_ellipse = self.getChannelObject("BeamShapeEllipse")
        self.chan_ImageZoom=self.getChannelObject("ImageZoom")

        self.connect(self.chan_beam_pos_x, "update", self.beam_position_changed)
        self.connect(self.chan_beam_pos_y, "update", self.beam_position_changed)
        self.connect(self.chan_ImageZoom, "update", self.beam_position_changed)
        self.connect(self.chan_beam_size_x,"update", self.beam_info_changed)
        self.connect(self.chan_beam_size_y,"update", self.beam_info_changed)
        self.connect(self.chan_beam_shape_ellipse,"update", self.beam_info_changed)
   
        print "beam x %s and y %s " % (self.chan_beam_pos_x.getValue(),self.chan_beam_pos_y.getValue())
        
        #self.polling = gevent.spawn(self._polling)

        self.aperture_pos_changed(self.aperture_hwobj.getApertureSize())

        self.beam_position[0] = 687 * self.chan_ImageZoom.getValue()
        self.beam_position[1] = 519 * self.chan_ImageZoom.getValue()
    """
    def _polling(self):
        old_beam_pos = [-1, -1]
        old_size = [-1, -1]
        old_shape = 'star'
        while self.keep_polling:
            try:
                beam_pos = self.get_beam_position()
                beam_dict = self.evaluate_beam_info()
                size_x, size_y, shape = beam_dict['size_x'], beam_dict['size_y'], beam_dict['shape']
                size = [size_x, size_y]
            except:
                time.sleep(1)
                continue
            if beam_pos != old_beam_pos:
                self.beam_position_changed()
                old_beam_pos = copy.copy(beam_pos)
            
            if size != old_size:
                old_size = copy.copy(size)
                self.beam_info_changed()
            if shape != old_shape:
                old_shape = copy.copy(shape)
                self.beam_info_changed()

            time.sleep(1)
    """
    def stop_polling(self):
        self.keep_polling = False

    def connectNotify(self, *args):
        self.evaluate_beam_info()
        self.emit_beam_info_change()
        #self.beam_position_changed()

    def beam_position_changed(self,value):
        self.get_beam_position()
        self.emit("beamPosChanged", (self.beam_position, ))
        print "xxxxxxxxxxxxxxxxxbeam position changed", self.beam_position

    def beam_info_changed(self,value):
	self.evaluate_beam_info()
	self.emit("beamInfoChanged", (self.beam_info_dict, ))
        print "ddddddddddddddddddddddddddddd", self.beam_info_dict
        print "xxxxxxxxxxxxxxxxxxxxxxxxxxbeam x %s and y %s " % (self.chan_beam_pos_x.getValue(),self.chan_beam_pos_y.getValue())
        """

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
        """

    def get_beam_position(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        #self.beam_position[0] = 687 * self.chan_ImageZoom.getValue()
        #self.beam_position[1] = 519 * self.chan_ImageZoom.getValue()
        #return self.beam_position
	if self.chan_ImageZoom.getValue() is not None:
            zoom = self.chan_ImageZoom.getValue()
            self.beam_position[0] = self.chan_beam_pos_x.getValue() * zoom
            self.beam_position[1] = self.chan_beam_pos_y.getValue() * zoom
        else:
            self.beam_position[0] = self.camera.getWidth() / 2
            self.beam_position[1] = self.camera.getHeight() / 2
        return self.beam_position


    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self,*args):
        BeamInfo.BeamInfo.evaluate_beam_info(self,*args)
        try:
            if self.chan_beam_shape_ellipse.getValue():
                self.beam_info_dict["shape"] = "ellipse"
            else:
                self.beam_info_dict["shape"] = "rectangle"
        except:    
                self.beam_info_dict["shape"] = "ellipse"
        curpos=self.aperture_hwobj.getCurrentPositionName()
        size_x = size_y = eval(str(curpos)) / 1000.0
	#if self.chan_beam_size_x.getValue() /1000.0 < size_x and self.chan_beam_size_y.getValue() / 1000.0 < size_y:
        #    self.beam_info_dict["size_x"] = self.chan_beam_size_x.getValue() / 1000.0
        #    self.beam_info_dict["size_y"] = self.chan_beam_size_y.getValue() / 1000.0
       # else:
	self.beam_info_dict["size_x"] = size_x
        self.beam_info_dict["size_y"] = size_y
	self.beam_info_dict['pos'] = self.beam_position
        return self.beam_info_dict
