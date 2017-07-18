"""
  File:  BIOMAXTangoLimaVideo.py

  Description:  This module implements a fix on top of TangoLimaVideoDevice
       for the inversion of width and height reported by the Tango Device Server from 
       Arinax.  

       18-07-2017 - This inversion is a bug in the device server and it should be fixed by Arinax
       soon. Once the bug is fixed this class can be deleted and TangoLimaVideoDevice can be 
       used instead


"""

from TangoLimaVideoDevice import TangoLimaVideoDevice

class BIOMAXTangoLimaVideo(TangoLimaVideoDevice):
    def get_image_dimensions(self):
        #return [self.device.image_width, self.device.image_height]
        return [self.device.image_height, self.device.image_width]

