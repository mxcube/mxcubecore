
from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects

from sample_changer.Cats90 import Cats90, SampleChangerState
import logging

class ALBACats(Cats90):

    def __init__(self, *args):
        Cats90.__init__(self, *args)

    def init(self):
        Cats90.init(self)

        self.shifts_channel = self.getChannelObject("shifts")
        self.phase_channel = self.getChannelObject("phase")

        if self._chnPathRunning is not None:
            self._chnPathRunning.connectSignal("update", self._updateRunningState)

        if self._chnPowered is not None:
            self._chnPowered.connectSignal("update", self._updatePoweredState)

    def read_diff_phase(self):
        return self.phase_channel.getValue()

    def load(self, sample=None, wait=True, wash=False):
        """
        Load a sample. 
        """
        if self.read_diff_phase().upper() != "TRANSFER":
            logging.getLogger("user_level_log").error("Cannot mount. Diffractometer is not in transfer phase")
            return

        sample = self._resolveComponent(sample)
        self.assertNotCharging()
        
        if self.hasLoadedSample():    
            if (wash is False) and self.getLoadedSample() == sample:
                raise Exception("The sample " + sample.getAddress() + " is already loaded")
            else:
                # Unload first / do a chained load
                pass

        return self._executeTask(SampleChangerState.Loading,wait,self._doLoad,sample)

    def load_ht(self, sample=None, wait=True, wash=False):
        logging.getLogger("user_level_log").error("Loading HT sample %s" % sample)

    def unload(self, sample_slot=None, wait=True):
        """
        Unload the sample. 
        If sample_slot=None, unloads to the same slot the sample was loaded from.        
        """
        if self.read_diff_phase().upper() != "TRANSFER":
            logging.getLogger("user_level_log").error("Cannot mount. Diffractometer is not in transfer phase")
            return

        logging.warning("SAMPLE CHANGER. Unloading sample")
        sample_slot = self._resolveComponent(sample_slot)
        self.assertNotCharging()

        #In case we have manually mounted we can command an unmount
        if not self.hasLoadedSample():
            raise Exception("No sample is loaded")

        logging.warning("  SAMPLE CHANGER. Unloading sample")
        return self._executeTask(SampleChangerState.Unloading,wait,self._doUnload,sample_slot)

    def isPowered(self):
        return self._chnPowered.getValue()

    def isPathRunning(self):
        return self._chnPathRunning.getValue()

    def hasLoadedSample(self):  # not used.  to use it remove _
        return self._chnSampleIsDetected.getValue()

    def _updateRunningState(self, value):
        self.emit('runningStateChanged', (value, ))

    def _updatePoweredState(self, value):
        self.emit('powerStateChanged', (value, ))

    def _doLoad(self,sample=None, shifts=None):
        """
        Loads a sample on the diffractometer. Performs a simple put operation if the diffractometer is empty, and 
        a sample exchange (unmount of old + mount of new sample) if a sample is already mounted on the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            
        shifts = self._get_shifts()

        selected=self.getSelectedSample()            

        if sample is not None:
            if sample != selected:
                self._doSelect(sample)
                selected=self.getSelectedSample()            
        else:
            if selected is not None:
                 sample = selected
            else:
               raise Exception("No sample selected")

        # calculate CATS specific lid/sample number
        lid = ((selected.getBasketNo() - 1) / 3) + 1
        sample = (((selected.getBasketNo() - 1) % 3) * 10) + selected.getVialNo()

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0" ]
        else:
            xshift, yshift, zshift = map(str,shifts)

        argin = ["2", str(lid), str(sample), "0", "0", xshift, yshift, zshift]
            
        if self.hasLoadedSample():
            if selected==self.getLoadedSample():
                raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")
            else:
                logging.getLogger("HWR").warning("  ==========CATS=== chained load sample, sending to cats:  %s" % argin)
                self._executeServerTask(self._cmdChainedLoad, argin)
        else:
            if self.cats_sample_on_diffr():
                logging.getLogger("HWR").warning("  ==========CATS=== sample on diffr, loading aborted") 
                self._updateState() # remove transient states like Loading. Reflect hardware state
            else:
                logging.getLogger("HWR").warning("  ==========CATS=== load sample, sending to cats:  %s" % argin)
                self._executeServerTask(self._cmdLoad, argin)

    def _doUnload(self,sample_slot=None, shifts=None):
        """
        Unloads a sample from the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            
        shifts = self._get_shifts()

        if (sample_slot is not None):
            self._doSelect(sample_slot)

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0" ]
        else:
            xshift, yshift, zshift = map(str,shifts)

        argin = ["2", "0", xshift, yshift, zshift]

        logging.getLogger("HWR").warning("  ==========CATS=== unload sample, sending to cats:  %s" % argin)
        self._executeServerTask(self._cmdUnload, argin)

    def _get_shifts(self):
        if self.shifts_channel is not None:
            shifts = self.shifts_channel.getValue()
        else:
            shifts = None
        return shifts

def test_hwo(hwo):
    print(" Is path running? ", hwo.isPathRunning())
    print(" Loading shifts:  ", hwo._get_shifts())
    print(" Sample on diffr :  ", hwo.cats_sample_on_diffr())

if  __name__ == '__main__':
    test()

