import BeamInfo

class MDBeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)
        
        self.chan_beam_position_hor = None
        self.chan_beam_position_ver = None
        self.chan_beam_size_microns = None
        self.chan_beam_shape_ellipse = None

    def init(self):
        BeamInfo.BeamInfo.init(self)

        self.chan_beam_position_hor = self.getChannelObject("beam_position_hor")
        if self.chan_beam_position_hor is not None: 
            self.chan_beam_position_hor.connectSignal("update", self.beam_pos_hor_changed)
        self.chan_beam_position_ver = self.getChannelObject("beam_position_ver")
        if self.chan_beam_position_ver is not None:
            self.chan_beam_position_ver.connectSignal("update", self.beam_pos_ver_changed)
        self.chan_beam_size_microns = self.getChannelObject("beam_size_microns")
        self.chan_beam_shape_ellipse = self.getChannelObject("beam_shape_ellipse")
 
    def beam_pos_hor_changed(self, value):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_position[0] = value
        self.emit("beamPosChanged", (self.beam_position, ))

    def beam_pos_ver_changed(self, value):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_position[1] = value 
        self.emit("beamPosChanged", (self.beam_position, ))

    def get_beam_position(self):
        """
        Descript. :
        Arguments :
        Return    :
        """
        if self.chan_beam_position_hor and self.chan_beam_position_ver:
            self.beam_position = [self.chan_beam_position_hor.getValue(), \
	                          self.chan_beam_position_ver.getValue()]
        return self.beam_position	

    def set_beam_position(self, beam_x, beam_y):
        """
        Descript. :
        Arguments :
        Return    :
        """
        self.beam_position = [beam_x, beam_y]
        if self.chan_beam_position_hor:
            self.chan_beam_position_hor.setValue(int(beam_x))
        if self.chan_beam_position_ver:
            self.chan_beam_position_ver.setValue(int(beam_y))
