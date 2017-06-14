import logging
from HardwareRepository.BaseHardwareObjects import Device

class EMBLBeamstop(Device):
    """
    Descrip. :
    """

    def __init__(self, name):
        """
        Descrip. :
        """
        Device.__init__(self, name)

        self.beamstop_distance = None
        self.default_beamstop_size = None
        self.default_beamstop_distance = None
        self.default_beamstop_direction = None 

        self.chan_beamstop_distance = None

    def init(self):
        """
        Descrip. :
        """
        self.default_beamstop_size = self.getProperty("defaultBeamstopSize")
        self.default_beamstop_distance = self.getProperty("defaultBeamstopDistance")
        self.default_beamstop_direction = self.getProperty("defaultBeamstopDirection")
 
        self.chan_beamstop_distance = self.getChannelObject('BeamstopDistance')
        if self.chan_beamstop_distance is not None:
            self.chan_beamstop_distance.connectSignal("update", self.beamstop_distance_changed)

    def isReady(self):
        """
        Descrip. :
        """
        return True

    def beamstop_distance_changed(self, value):
        self.beamstop_distance = value
	self.emit('beamstopDistanceChanged', (value))

    def set_positions(self, position):
        if self.chan_beamstop_distance is not None:
           self.chan_beamstop_distance.setValue(position)
           self.beamstop_distance_changed(position)           

    def moveToPosition(self, name):
        pass
 
    def get_beamstop_size(self):
        """
        Descrip. :
        """
        return self.default_beamstop_size

    def get_beamstop_distance(self):
        """
        Descrip. :
        """
        beamstop_distance = None
        if self.chan_beamstop_distance is not None:
            beamstop_distance = self.chan_beamstop_distance.getValue()

        if beamstop_distance is None:
            return self.default_beamstop_distance
        else:
            return beamstop_distance

    def get_beamstop_direction(self):
        """
        Descrip. :
        """
        return self.default_beamstop_direction

    def update_values(self):
        self.beamstop_distance =  self.chan_beamstop_distance.getValue()
        self.emit('beamstopDistanceChanged', (self.beamstop_distance))
        
