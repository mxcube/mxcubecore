
from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects

from sample_changer.Cats90 import Cats90, SampleChangerState
import logging
import time

class ALBACats(Cats90):

    def __init__(self, *args):
        Cats90.__init__(self, *args)

    def init(self):
        Cats90.init(self)

        self.shifts_channel = self.getChannelObject("shifts")
        self.phase_channel = self.getChannelObject("phase")
        self.go_transfer_cmd = self.getCommandObject("go_transfer")
        self.super_state_channel = self.getChannelObject("super_state")

        self._cmdLoadHT = self.getCommandObject("_cmdLoadHT")
        self._cmdChainedLoadHT = self.getCommandObject("_cmdChainedLoadHT")
        self._cmdUnloadHT = self.getCommandObject("_cmdUnloadHT")

        
        logging.getLogger("HWR").error("LoadHT: %s" % str(self._cmdLoadHT))
        logging.getLogger("HWR").error("UnloadHT: %s" % str(self._cmdUnloadHT))
        logging.getLogger("HWR").error("ChainedHT: %s" % str(self._cmdChainedLoadHT))

        if self._chnPathRunning is not None:
            self._chnPathRunning.connectSignal("update", self._updateRunningState)

        if self._chnPowered is not None:
            self._chnPowered.connectSignal("update", self._updatePoweredState)

    def diff_send_transfer(self, timeout = 40):

        if self.read_super_phase().upper() == "TRANSFER":
            logging.getLogger("user_level_log").error("Supervisor is already in transfer phase")
            return True

        logging.getLogger("user_level_log").error("Supervisor is not in transfer phase")

        self.go_transfer_cmd()   

        while True:
            state = str( self.super_state_channel.getValue() )
            if state == "ON": 
                logging.getLogger("user_level_log").error("Supervisor is in ON state. Returning") 
                break
            elif str(state) != "MOVING":
                logging.getLogger("user_level_log").error("Supervisor is in a funny state %s" % str(state))
                return False
            
            logging.getLogger("HWR").debug("Supervisor waiting to get to transfer phase")
            time.sleep(0.2)

        time.sleep(0.1)
        if self.read_super_phase().upper() != "TRANSFER":
            logging.getLogger("user_level_log").error("Supervisor is not yet in transfer phase. Aborting load")
            return False
        else:
            return True

    def read_super_phase(self):
        return self.phase_channel.getValue()

    def load(self, sample=None, wait=False, wash=False):
        """
        Load a sample. 
        """
        sample = self._resolveComponent(sample)
        self.assertNotCharging()
        
        if self.hasLoadedSample():    
            if (wash is False) and self.getLoadedSample() == sample:
                raise Exception("The sample " + sample.getAddress() + " is already loaded")
            else:
                # Unload first / do a chained load
                pass

        return self._executeTask(SampleChangerState.Loading,wait,self._doLoad,sample)

    def load_ht(self, sample=None, wait=False, wash=False):
        logging.getLogger("user_level_log").error("Loading HT sample %s" % sample)
        return self._executeTask(SampleChangerState.Loading,wait,self._doLoad,sample,None,True)

    def unload(self, sample_slot=None, wait=False):
        """
        Unload the sample. 
        If sample_slot=None, unloads to the same slot the sample was loaded from.        
        """
        sample_slot = self._resolveComponent(sample_slot)

        logging.warning("SAMPLE CHANGER. Unloading sample %s" % str(sample_slot))
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

    def _doLoad(self, sample=None, shifts=None, use_ht=False):
        """
        Loads a sample on the diffractometer. Performs a simple put operation if the diffractometer is empty, and 
        a sample exchange (unmount of old + mount of new sample) if a sample is already mounted on the diffractometer.

        :returns: None
        :rtype: None
        """
        if not self._chnPowered.getValue():
            raise Exception("CATS power is not enabled. Please switch on arm power before transferring samples.")
            
        ret = self.diff_send_transfer()

        if ret is False:
            logging.getLogger("user_level_log").error("Supervisor cmd transfer phase returned an error.")
            return

        # obtain mounting offsets from diffr
        shifts = self._get_shifts()

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0" ]
        else:
            xshift, yshift, zshift = map(str,shifts)

        # get sample selection
        selected=self.getSelectedSample()            

        logging.getLogger("HWR").debug("  ==========CATS=== selected sample is %s (prev %s)" % (str(selected) , str(sample)))

        if not use_ht:
            if sample is not None:
                if sample != selected:
                    self._doSelect(sample)
                    selected=self.getSelectedSample()            
            else:
                if selected is not None:
                     sample = selected
                else:
                   raise Exception("No sample selected")
        else:
            selected = None

        # some cancel cases
        if not use_ht and self.hasLoadedSample() and selected==self.getLoadedSample():
            raise Exception("The sample " + str(self.getLoadedSample().getAddress()) + " is already loaded")

        if not self.hasLoadedSample() and self.cats_sample_on_diffr():
            logging.getLogger("HWR").warning("  ==========CATS=== sample on diffr, loading aborted") 
            self._updateState() # remove transient states like Loading. Reflect hardware state
            return
        # end some cancel cases
 
        # if load_ht
        loaded_ht = self.is_loaded_ht()

        #
        # Loading HT sample
        #
        if use_ht:  # loading HT sample

            if loaded_ht == -1: # has loaded but it is not HT
               # first unmount (non HT)
               logging.getLogger("HWR").warning("  ==========CATS=== mix load/unload dewar vs HT (NOT IMPLEMENTED YET)") 
               return

            argin = ["2", str(sample), "0", "0", xshift, yshift, zshift]
            logging.getLogger("HWR").warning("  ==========CATS=== about to load HT. %s" % str(argin))
            if loaded_ht == 1:  # has ht loaded
                self._executeServerTask(self._cmdChainedLoadHT, argin)
            else:
                self._executeServerTask(self._cmdLoadHT, argin)

        #
        # Loading non HT sample
        #
        else:
            if loaded_ht == 1:  # has an HT sample mounted
               # first unmount HT
               logging.getLogger("HWR").warning("  ==========CATS=== mix load/unload dewar vs HT (NOT IMPLEMENTED YET)") 
               return

            # calculate CATS specific lid/sample number
            lid = ((selected.getBasketNo() - 1) / 3) + 1
            sample = (((selected.getBasketNo() - 1) % 3) * 10) + selected.getVialNo()

            argin = ["2", str(lid), str(sample), "0", "0", xshift, yshift, zshift]

            if loaded_ht == -1:  # has a loaded but it is not an HT
                logging.getLogger("HWR").warning("  ==========CATS=== about to load. read barcode option is  %s" % self.read_datamatrix)
                if self.read_datamatrix and self._cmdChainedLoadBarcode is not None:
                    logging.getLogger("HWR").warning("  ==========CATS=== chained load sample (barcode), sending to cats:  %s" % argin)
                    self._executeServerTask(self._cmdChainedLoadBarcode, argin)
                else:
                    logging.getLogger("HWR").warning("  ==========CATS=== chained load sample, sending to cats:  %s" % argin)
                    self._executeServerTask(self._cmdChainedLoad, argin)
            elif loaded_ht == 0:
                logging.getLogger("HWR").warning("  ==========CATS=== about to load. read barcode option is  %s" % self.read_datamatrix)
                if self.read_datamatrix and self._cmdLoadBarcode is not None:
                    logging.getLogger("HWR").warning("  ==========CATS=== load sample (barcode), sending to cats:  %s" % argin)
                    self._executeServerTask(self._cmdLoadBarcode, argin)
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
            
        ret = self.diff_send_transfer()

        if ret is False:
            logging.getLogger("user_level_log").error("Supervisor cmd transfer phase returned an error.")
            return

        shifts = self._get_shifts()

        if (sample_slot is not None):
            self._doSelect(sample_slot)

        loaded_ht = self.is_loaded_ht()

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0" ]
        else:
            xshift, yshift, zshift = map(str,shifts)

        argin = ["2", "0", xshift, yshift, zshift]

        logging.getLogger("HWR").warning("  ==========CATS=== unload sample, sending to cats:  %s" % argin)
        if loaded_ht == 1:
            self._executeServerTask(self._cmdUnloadHT, argin)
        else:
            self._executeServerTask(self._cmdUnload, argin)

    def _get_shifts(self):
        if self.shifts_channel is not None:
            shifts = self.shifts_channel.getValue()
        else:
            shifts = None
        return shifts

    def is_loaded_ht(self):
        """
        UNFINISHED
        :returns:
           1 : has loaded ht
           0 : nothing loaded
          -1 : loaded but not ht
        """
        sample_lid = self._chnLidLoadedSample.getValue()

        if self.hasLoadedSample():
            if sample_lid == 100:
                return 1
            else:
                return -1
        else:
            return 0
    

def test_hwo(hwo):
    print(" Is path running? ", hwo.isPathRunning())
    print(" Loading shifts:  ", hwo._get_shifts())
    print(" Sample on diffr :  ", hwo.cats_sample_on_diffr())
    print(" Baskets :  ", hwo.basket_presence)
    print(" Baskets :  ", hwo.getBasketList())
    print(" Samples :  ", [sample[-1] for sample in hwo.getSampleList()])


if  __name__ == '__main__':
    test()

