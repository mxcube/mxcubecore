# Hardware object for MCCE list.

# Tue 2 Oct 2007 14:32:38
# Wed 11 Apr 2007 18:12:11
# Cyril.Guilloud@esrf.fr

# TODO :
# -check MCCE_SETUPOK to be sure to have a good initialization before
#  creating the brick.
# -auto-refactoring after a new mccesetup ?
#

from HardwareRepository.BaseHardwareObjects import Equipment



class Mcce(Equipment):
    def init(self):

        self.mcce_freq = None
        self.mcce_gain = None
        self.mcce_pol = None
        self.mcce_range = None
        self.mcce_name = None
        self.mcce_type = None
        self.mcce_dev = None

        # print "MCCE-HWO--self.device_number=" , self.device_number
        self.mcce_number = self.device_number

        """
        Connection of channels (monitored variables)
        """
        #  channel(update) ----> functions to emit sig.
        self.mcceDevChan = self.getChannelObject("mcce_dev")
        if self.mcceDevChan is not None:
            self.mcceDevChan.connectSignal("update", self.updateMcceDev)

        self.mcceTypeChan = self.getChannelObject("mcce_type")
        if self.mcceTypeChan is not None:
            self.mcceTypeChan.connectSignal("update", self.updateMcceType)

        self.mcceRangeChan = self.getChannelObject("mcce_range")
        if self.mcceRangeChan is not None:
            self.mcceRangeChan.connectSignal("update", self.updateMcceRange)

        self.mcceGainChan = self.getChannelObject("mcce_gain")
        if self.mcceGainChan is not None:
            self.mcceGainChan.connectSignal("update", self.updateMcceGain)

        self.mcceFreqChan = self.getChannelObject("mcce_freq")
        if self.mcceFreqChan is not None:
            self.mcceFreqChan.connectSignal("update", self.updateMcceFreq)

        self.mccePolChan = self.getChannelObject("mcce_pol")
        if self.mccePolChan is not None:
            self.mccePolChan.connectSignal("update", self.updateMccePol)

        self.mcceNameChan = self.getChannelObject("mcce_name")
        if self.mcceNameChan is not None:
            self.mcceNameChan.connectSignal("update", self.updateMcceName)

        """
        HWO -> SPEC
        Conections to spec commands
        """
        # <command type="spec" name="mccerange_cmd"   >mccerange</command>
        # <command type="spec" name="mccepolarity_cmd">mccepolarity</command>
        # <command type="spec" name="mccefreq_cmd"    >mccefreq</command>
        # <command type="spec" name="mccegain_cmd"    >mccegain</command>

        self.mcceRangeCmd = self.getCommandObject("mccerange_cmd")
        self.mcceFreqCmd = self.getCommandObject("mccefreq_cmd")
        self.mcceGainCmd = self.getCommandObject("mccegain_cmd")
        self.mccePolCmd = self.getCommandObject("mccepolarity_cmd")

    # 3
    # EMIT SIGNALS    :  HWO   --->   GUI
    #######################

    def updateMcceDev(self, device):
        print("--McceHwObj--updateMcceDev--", device, " number=", self.mcce_number)
        self.mcce_dev = device
        self.emit("hwoConnected", (device,))
        self.emit("updateDev", (device,))

    def updateMcceName(self, name):
        print("--McceHwObj--updateMcceName--, ", name, " number=", self.mcce_number)
        self.mcce_name = name
        self.emit("nameChanged", (name,))

    def updateMcceType(self, mtype):
        print("--McceHwObj--updateMcceType-- ", mtype, " number=", self.mcce_number)
        self.mcce_type = mtype
        self.emit("updateType", (mtype,))

    def updateMcceRange(self, range):
        print("--McceHwObj--updateMcceRange-- ", range, " number=", self.mcce_number)
        self.mcce_range = range
        self.emit("updateRange", (range,))

    def updateMcceFreq(self, freq):
        print("--McceHwObj--updateMcceFreq-- ", freq, " number=", self.mcce_number)
        self.mcce_freq = freq
        self.emit("updateFreq", (freq,))

    def updateMcceGain(self, gain):
        print("--McceHwObj--updateMcceGain-- ", gain, " number=", self.mcce_number)
        self.mcce_gain = gain
        self.emit("updateGain", (gain,))

    def updateMccePol(self, pol):
        print("--McceHwObj--updateMccePol-- ", pol, " number=", self.mcce_number)
        self.mcce_pol = pol
        self.emit("updatePol", (pol,))
