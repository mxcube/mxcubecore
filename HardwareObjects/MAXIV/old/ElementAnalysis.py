import threading
import string
import os
import time
import qt
import logging
from SpecClient.SpecCommand import SpecCommand
from SpecClient import SpecClientError
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Procedure

print "Custom ElementAnalysis loaded"


class ElementAnalysis(Procedure):

    MANDATORY_CHANNELS = {"updateGraph": "updateGraph", "clfluorState": "clfluorState"}
    MANDATORY_CMDS = {
        "doScan": "doScan",
        "detectorIn": "detectorIn",
        "detectorOut": "detectorOut",
        "setParameters": "setParameters",
    }

    def init(self):

        #        print "\n\n\n\n\n ElemenyAnalysis:init...................\n\n\n\n"

        self.configOk = True
        if self.getProperty("specversion") is None:
            logging.getLogger().error(
                "ElementAnalysis: you must specify a spec version"
            )
            self.configOk = False
        else:
            for chan in ElementAnalysis.MANDATORY_CHANNELS:
                # print "********* - chan: " , chan
                desc = ElementAnalysis.MANDATORY_CHANNELS[chan]
                # print "********** - desc: ", desc
                try:
                    channel = self.getChannelObject(
                        chan
                    )  # channel == <SpecChannel> (HardwareRepository.Command.Spec.py)
                    # print "xxxxxxxxx channel value: " , channel.getValue()
                    # print channel.getValue()
                    # channel.getValue()
                except KeyError:
                    channel = None
                if channel is None:
                    logging.getLogger().error(
                        "ElementAnalysis: you must specify the %s spec channel" % desc
                    )
                    self.configOk = False
                else:
                    try:
                        exec("self.connect(channel,'update',self.%sUpdate)" % chan)
                    except AttributeError:
                        pass
                exec("self.%sChannel=channel" % chan)

            self.energy = self.getChannelObject("energy")
            self.energy_value = self.energy.getValue()
            if self.energy is not None:
                self.energy.connectSignal("update", self.energyChanged)

            # print "<<<<<<<<<<self.%sChannel=channel"% chan, channel
            # print "<<<<<<<<<<self.%sChannel.getValue()"% chan, channel.getValue()
            #           commands=self.getCommands()
            #            print "------------commands", commands
            for mandatory_cmd in ElementAnalysis.MANDATORY_CMDS:
                desc = ElementAnalysis.MANDATORY_CMDS[mandatory_cmd]

                commands = self.getCommands()
                # print "------------commands", commands
                # print "xxxxxxxxxxxxxx-commands.getcommandNamesList()"
                # print self.getCommandNamesList()
                # print "-------mandatory_cmd", mandatory_cmd

                cmd_found = None
                for (
                    cmd
                ) in (
                    commands
                ):  # cmd == <SpecCommand> (HardwareRepository.Command.Spec.py)
                    # print "--------for cmd in commands: cmd", cmd
                    if cmd.name() == mandatory_cmd:
                        cmd_found = cmd
                        try:
                            exec(
                                "cmd.connectSignal('commandReplyArrived', self.%sEnded)"
                                % mandatory_cmd
                            )
                        except AttributeError:
                            pass
                        try:
                            exec(
                                "cmd.connectSignal('commandBeginWaitReply', self.%sStarted)"
                                % mandatory_cmd
                            )
                        except AttributeError:
                            pass
                        try:
                            exec(
                                "cmd.connectSignal('commandFailed', self.%sFailed)"
                                % mandatory_cmd
                            )
                        except AttributeError:
                            pass
                        try:
                            exec(
                                "cmd.connectSignal('commandAborted', self.%sAborted)"
                                % mandatory_cmd
                            )
                        except AttributeError:
                            pass
                        break
                    else:
                        pass
                        # print "--------else:"

                if cmd_found is None:
                    logging.getLogger().error(
                        "ElementAnalysis: you must specify the %s command" % desc
                    )
                    self.configOk = False
                exec("self.%sCmd=cmd_found" % mandatory_cmd)
                # print " "
                # print ("------------- Added command: self.%sCmd=cmd_found"% mandatory_cmd )
                # print ("-------------                     : mandatory_cmd", mandatory_cmd)
                # print ("-------------                     : cmd_found", cmd_found  )
                # print " "

            self.helpText = self.getProperty("helptext")
            # Quick fix. Krister 090424

            self.defaultDataDir = "/data/data1"
            # self.defaultDataDir=self.getProperty("defaultdatadir")

            if self.configOk:
                self.doScanCmd.connectSignal("connected", self.connected)
                self.doScanCmd.connectSignal("connected", self.disconnected)
                self.doScanCmd.connectSignal("commandReady", self.cmdReady)
                self.doScanCmd.connectSignal("commandNotReady", self.cmdNotReady)
                if self.doScanCmd.isSpecConnected():
                    self.connected()
        self.lock = threading.Lock()

    # Locks the Qt display, emits a signal, and unlocks Qt
    def safeEmit(self, signal, params):
        qt.qApp.lock()
        try:
            self.emit(signal, params)
        finally:
            qt.qApp.unlock()

    # Checks if one can do a scan
    def isReady(self):
        if not self.configOk:
            return False

        if self.doScanCmd.isSpecReady():
            if not self.lock.locked():
                return True
        return False

    # Checks if spec is connected
    def isSpecConnected(self):
        if not self.configOk:
            return False
        if self.doScanCmd is None:
            return False
        return self.doScanCmd.isSpecConnected()

    # Called when spec is disconnected
    def disconnected(self):
        # if self.lock.locked():
        #    return
        self.safeEmit("disconnected", ())

    # Called when spec is connected
    def connected(self):
        # if self.lock.locked():
        #    return
        self.safeEmit("connected", ())

    # Called when spec is not ready
    def cmdNotReady(self):
        if self.doScanCmd.isSpecConnected():
            state = "BUSY"
        else:
            state = "ERROR"
        self.safeEmit("specState", (state,))
        # print "ElementAnalysis: self.safeEmit('specState', (state,)) "

    # Called when spec is ready
    def cmdReady(self):
        self.safeEmit("specState", ("READY",))
        # print "ElementAnalysis: self.safeEmit('specState', ('READY',)) "

    def cmdGetReady(self):
        if self.doScanCmd is None:
            state = "UNKNOWN"
        else:
            if self.doScanCmd.isSpecConnected():
                if self.doScanCmd.isSpecReady():
                    state = "READY"
                else:
                    state = "BUSY"
            else:
                state = "ERROR"
        return state

    def startScan(self, minE, maxE, expTime):
        # print "starting startSan with minE %f, maxE %f and Time%f"%
        # (minE,maxE,expTime,)
        if minE == maxE:
            s = "Min energy and max energy are equal"
            return s
        if expTime <= 0:
            s = "Exposure time < 0"
            return s
        if minE < 0.0 or minE < 0.0:
            s = "Negative energy not allowed"
            return s
        if minE > maxE:
            s = "Min energy > Max energy.\nTry again."
            return s
        if maxE > 16.5:
            s = "Energies above 16.5 cannot be observed."
            return s
        # Something is wrong in the hardware. Using 20 keV range always
        # elif maxE > 10.0:
        #    mmrange=1
        #    mmread1=20.0
        else:
            mmrange = 1
            mmread1 = 20.0
        mmread0 = 0
        # print "setParameters %f, %f , %f"% (mmrange,mmread0,mmread1)
        self.setParametersCmd(mmrange, mmread0, mmread1)

        self.doScanCmd(expTime)

        return 0

    def abortScan(self):
        self.doScanCmd.abort()

    def updateGraphUpdate(self, val):
        if val:
            XValues = self.getChannelObject("mxdatax").getValue()
            YValues = self.getChannelObject("mxdatay").getValue()
            self.safeEmit("newDataValues", (XValues, YValues))

    # change text on button in brick, recived by
    def clfluorStateUpdate(self, state):
        self.safeEmit("clfluorState", (state,))
        # print "------ElementAnalysis:  clfluorStateUpdate(self,state):", state
        # print "clfluorStateChannel", self.clfluorStateChannel

    #
    # state ==1 means detector is out
    #
    def setCLFluor(self, state):
        if not state:
            self.detectorInCmd()
            # print "-------------ElementAnalysis:  self.detectorInCmd() ",
            # self.detectorInCmd
        else:
            self.detectorOutCmd()
            # print "-------------ElementAnalysis:  self.detectorOutCmd() ", self.detectorOutCmd
        # print "clfluorStateChannel", self.clfluorStateChannel
        self.clfluorStateUpdate(state)

    def getElementEdges(self, element):
        s = "%s 12.0\n" % element
        self.element = element
        self.xraycalc = qt.QProcess("/home/blissadm/local/MAXapplications/xraycalc")
        self.xraycalc.start()
        # print self.xraycalc.isRunning()
        self.xraycalc.writeToStdin(s)
        self.xraycalc.writeToStdin("QU\n")
        qt.QObject.connect(
            self.xraycalc, qt.SIGNAL("processExited()"), self.processElementEdges
        )

    def getEnergies(self, energy):
        # print "getEnegries",energy
        s = "XX %f\n" % energy
        self.xraycalc = qt.QProcess("/home/blissadm/local/MAXapplications/xraycalc")
        self.xraycalc.start()
        # print self.xraycalc.isRunning()
        self.xraycalc.writeToStdin(s)
        self.xraycalc.writeToStdin("QU\n")
        qt.QObject.connect(
            self.xraycalc, qt.SIGNAL("processExited()"), self.processEnergies
        )

    def processElementEdges(self):
        f = file("xcalc.dat", "r")
        data = []
        for line in f:
            data.append(line.strip())
        # print data
        f.close()
        data = data[4]
        qt.QObject.disconnect(
            self.xraycalc, qt.SIGNAL("processExited()"), self.processElementEdges
        )
        self.safeEmit("processElementEdgesUpdated", (data, self.element))

    def processEnergies(self):
        # print "processEnergies"
        f = file("xcalc.dat", "r")
        data = []
        for line in f:
            data.append(line.strip())
        # print data
        f.close()
        qt.QObject.disconnect(
            self.xraycalc, qt.SIGNAL("processExited()"), self.processEnergies
        )
        self.safeEmit("processEnergiesUpdated", (data,))

    def energyChanged(self, value):
        self.energy_value = self.energy.getValue()
        self.emit("energyUpdated")
