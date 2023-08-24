import logging
import PyChooch
import os
import time
import math
import gevent
import Xane

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from mxcubecore.BaseHardwareObjects import Equipment
from mxcubecore.TaskUtils import cleanup
from mxcubecore import HardwareRepository as HWR


class SOLEILEnergyScan(Equipment):
    def init(self):
        logging.getLogger("HWR").info(
            "#############################    EnergyScan: INIT HWOBJ  ###################"
        )
        self.ready_event = gevent.event.Event()
        self.scanning = None
        self.moving = None
        self.energyScanArgs = None
        self.archive_prefix = None
        self.energy2WavelengthConstant = None
        self.defaultWavelength = None
        self._element = None
        self._edge = None
        self.do_energy_scan = None
        try:
            self.defaultWavelengthChannel = self.get_channel_object(
                "default_wavelength"
            )
        except KeyError:
            self.defaultWavelengthChannel = None
        else:
            if self.defaultWavelengthChannel is not None:
                self.defaultWavelengthChannel.connect_signal(
                    "connected", self.sConnected
                )
                self.defaultWavelengthChannel.connect_signal(
                    "disconnected", self.sDisconnected
                )

        if self.defaultWavelengthChannel is None:
            # MAD beamline
            try:
                self.energyScanArgs = self.get_channel_object("escan_args")
            except KeyError:
                logging.getLogger("HWR").warning(
                    "EnergyScan: error initializing energy scan arguments (missing channel)"
                )
                self.energyScanArgs = None

            try:
                self.scanStatusMessage = self.get_channel_object("scanStatusMsg")
            except KeyError:
                self.scanStatusMessage = None
                logging.getLogger("HWR").warning(
                    "EnergyScan: energy messages will not appear (missing channel)"
                )
            else:
                self.connect(self.scanStatusMessage, "update", self.scanStatusChanged)

            try:
                self.do_energy_scan.connect_signal(
                    "commandReplyArrived", self.scanCommandFinished
                )
                self.do_energy_scan.connect_signal(
                    "commandBeginWaitReply", self.scanCommandStarted
                )
                self.do_energy_scan.connect_signal(
                    "commandFailed", self.scanCommandFailed
                )
                self.do_energy_scan.connect_signal(
                    "commandAborted", self.scanCommandAborted
                )
                self.do_energy_scan.connect_signal(
                    "commandReady", self.scanCommandReady
                )
                self.do_energy_scan.connect_signal(
                    "commandNotReady", self.scanCommandNotReady
                )
            except AttributeError as diag:
                logging.getLogger("HWR").warning(
                    "EnergyScan: error initializing energy scan (%s)" % str(diag)
                )
                self.do_energy_scan = Xanes  # .xanes(None, None) #None
            else:
                self.do_energy_scan.connect_signal("connected", self.sConnected)
                self.do_energy_scan.connect_signal("disconnected", self.sDisconnected)

            self.previousResolution = None
            self.lastResolution = None

            if HWR.beamline.lims is None:
                logging.getLogger("HWR").warning(
                    "EnergyScan: you should specify the database hardware object"
                )
            self.scanInfo = None

            self.cryostreamHO = self.get_object_by_role("cryostream")
            if self.cryostreamHO is None:
                logging.getLogger("HWR").warning(
                    "EnergyScan: you should specify the cryo stream hardware object"
                )

            self.machcurrentHO = self.get_object_by_role("machcurrent")
            if self.machcurrentHO is None:
                logging.getLogger("HWR").warning(
                    "EnergyScan: you should specify the machine current hardware object"
                )

            self.fluodetectorHO = self.get_object_by_role("fluodetector")
            if self.fluodetectorHO is None:
                logging.getLogger("HWR").warning(
                    "EnergyScan: you should specify the fluorescence detector hardware object"
                )

            try:
                # self.moveEnergy.connect_signal('commandReplyArrived', self.moveEnergyCmdFinished)
                # self.moveEnergy.connect_signal('commandBeginWaitReply', self.moveEnergyCmdStarted)
                # self.moveEnergy.connect_signal('commandFailed', self.moveEnergyCmdFailed)
                # self.moveEnergy.connect_signal('commandAborted', self.moveEnergyCmdAborted)
                self.moveEnergy.connect_signal("commandReady", self.moveEnergyCmdReady)
                self.moveEnergy.connect_signal(
                    "commandNotReady", self.moveEnergyCmdNotReady
                )
            except AttributeError as diag:
                logging.getLogger("HWR").warning(
                    "EnergyScan: error initializing move energy (%s)" % str(diag)
                )
                self.moveEnergy = None

            if HWR.beamline.energy is not None:
                HWR.beamline.energy.connect("valueChanged", self.energyPositionChanged)
                HWR.beamline.energy.connect("stateChanged", self.energyStateChanged)
                HWR.beamline.energy.connect("limitsChanged", self.energyLimitsChanged)
            if HWR.beamline.resolution is None:
                logging.getLogger("HWR").warning(
                    "EnergyScan: no resolution motor (unable to restore it after moving the energy)"
                )
            else:
                HWR.beamline.resolution.connect(
                    "valueChanged", self.resolutionPositionChanged
                )

        self.thEdgeThreshold = self.get_property("theoritical_edge_threshold")
        if self.thEdgeThreshold is None:
            self.thEdgeThreshold = 0.01

        if self.is_connected():
            self.sConnected()
        logging.getLogger("HWR").info(
            "#############################    EnergyScan: INIT HWOBJ IS FINISHED ###################"
        )

    def is_connected(self):
        if self.defaultWavelengthChannel is not None:
            # single wavelength beamline
            try:
                return self.defaultWavelengthChannel.is_connected()
            except Exception:
                return False
        else:
            try:
                return self.do_energy_scan.is_connected()
            except Exception:
                return False

    def resolutionPositionChanged(self, res):
        self.lastResolution = res

    def energyStateChanged(self, state):
        if state == HWR.beamline.energy.READY:
            if HWR.beamline.resolution is not None:
                HWR.beamline.resolution.dist2res()

    # Handler for spec connection
    def sConnected(self):
        self.emit("connected", ())

    # Handler for spec disconnection
    def sDisconnected(self):
        self.emit("disconnected", ())

    def setElement(self):
        logging.getLogger("HWR").debug("EnergyScan: setElement")
        self.emit("setElement", (self._element, self._edge))

    def newPoint(self, x, y):
        logging.getLogger("HWR").debug("EnergyScan:newPoint")
        logging.info("EnergyScan newPoint %s, %s" % (x, y))
        self.emit("addNewPoint", (x, y))
        self.emit("newScanPoint", (x, y))

    def newScan(self, scanParameters):
        logging.getLogger("HWR").debug("EnergyScan:newScan")
        self.emit("newScan", (scanParameters,))

    # # Energy scan commands
    # def canScanEnergy(self):
    #     if not self.is_connected():
    #         return False
    #     if self.energy2WavelengthConstant is None or self.energyScanArgs is None:
    #         return False
    #     return self.do_energy_scan is not None

    def start_energy_scan(
        self, element, edge, directory, prefix, session_id=None, blsample_id=None
    ):
        self._element = element
        self._edge = edge
        logging.getLogger("HWR").debug(
            "EnergyScan: starting energy scan %s, %s" % (self._element, self._edge)
        )
        self.setElement()
        self.xanes = Xanes.xanes(
            self,
            element,
            edge,
            directory,
            prefix,
            session_id,
            blsample_id,
            plot=False,
            test=False,
        )
        self.scanInfo = {
            "sessionId": session_id,
            "blSampleId": blsample_id,
            "element": element,
            "edgeEnergy": edge,
        }
        if self.fluodetectorHO is not None:
            self.scanInfo["fluorescenceDetector"] = self.fluodetectorHO.username
        if not os.path.isdir(directory):
            logging.getLogger("HWR").debug(
                "EnergyScan: creating directory %s" % directory
            )
            try:
                os.makedirs(directory)
            except OSError as diag:
                logging.getLogger("HWR").error(
                    "EnergyScan: error creating directory %s (%s)"
                    % (directory, str(diag))
                )
                self.emit("scanStatusChanged", ("Error creating directory",))
                return False

        scanParameter = {}
        scanParameter["title"] = "Energy Scan"
        scanParameter["xlabel"] = "Energy in keV"
        scanParameter["ylabel"] = "Normalized counts"
        self.newScan(scanParameter)

        # try:
        # curr=self.energyScanArgs.get_value()
        # except:
        # logging.getLogger("HWR").exception('EnergyScan: error getting energy scan parameters')
        # self.emit('scanStatusChanged', ("Error getting energy scan parameters",))
        # return False
        # try:
        # curr["escan_dir"]=directory
        # curr["escan_prefix"]=prefix
        # except TypeError:
        curr = {}
        curr["escan_dir"] = directory
        curr["escan_prefix"] = prefix

        self.archive_prefix = prefix

        try:
            # self.energyScanArgs.set_value(curr)
            logging.getLogger("HWR").debug(
                "EnergyScan: current energy scan parameters (%s, %s, %s, %s)"
                % (element, edge, directory, prefix)
            )
        except Exception:
            logging.getLogger("HWR").exception(
                "EnergyScan: error setting energy scan parameters"
            )
            self.emit("scanStatusChanged", ("Error setting energy scan parameters",))
            return False
        try:
            # self.do_energy_scan("%s %s" % (element,edge))
            self.scanCommandStarted()
            self.xanes.scan()  # start() #scan()
            self.scanCommandFinished("success")
        except Exception:
            import traceback

            logging.getLogger("HWR").error(
                "EnergyScan: problem calling sequence %s" % traceback.format_exc()
            )
            self.emit("scanStatusChanged", ("Error problem spec macro",))
            return False
        return True

    def cancelEnergyScan(self, *args):
        logging.info("SOLEILEnergyScan: canceling the scan")
        if self.scanning:
            # self.do_energy_scan.abort()
            self.xanes.abort()
            self.ready_event.set()

    def scanCommandReady(self):
        if not self.scanning:
            self.emit("energyScanReady", (True,))

    def scanCommandNotReady(self):
        if not self.scanning:
            self.emit("energyScanReady", (False,))

    def scanCommandStarted(self, *args):
        self.scanInfo["startTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit("energyScanStarted", ())

    def scanCommandFailed(self, *args):
        self.scanInfo["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.storeEnergyScan()
        self.emit("energyScanFailed", ())
        self.ready_event.set()

    def scanCommandAborted(self, *args):
        self.emit("energyScanFailed", ())
        self.ready_event.set()

    def scanCommandFinished(self, result, *args):
        logging.getLogger("HWR").debug("EnergyScan: energy scan result is %s" % result)
        with cleanup(self.ready_event.set):
            self.scanInfo["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
            logging.getLogger("HWR").debug(
                "EnergyScan: energy scan result is %s" % result
            )
            self.scanning = False
            if result == -1:
                self.storeEnergyScan()
                self.emit("energyScanFailed", ())
                return

            try:
                t = float(result["transmissionFactor"])
            except Exception:
                pass
            else:
                self.scanInfo["transmissionFactor"] = t
            try:
                et = float(result["exposureTime"])
            except Exception:
                pass
            else:
                self.scanInfo["exposureTime"] = et
            try:
                se = float(result["startEnergy"])
            except Exception:
                pass
            else:
                self.scanInfo["startEnergy"] = se
            try:
                ee = float(result["endEnergy"])
            except Exception:
                pass
            else:
                self.scanInfo["endEnergy"] = ee

            try:
                bsX = float(result["beamSizeHorizontal"])
            except Exception:
                pass
            else:
                self.scanInfo["beamSizeHorizontal"] = bsX

            try:
                bsY = float(result["beamSizeVertical"])
            except Exception:
                pass
            else:
                self.scanInfo["beamSizeVertical"] = bsY

            try:
                self.thEdge = float(result["theoreticalEdge"]) / 1000.0
            except Exception:
                pass

            self.emit("energyScanFinished", (self.scanInfo,))
            time.sleep(0.1)
            self.emit("energyScanFinished2", (self.scanInfo,))

    def do_chooch(self, elt, edge, scanArchiveFilePrefix, scanFilePrefix):
        # symbol = "_".join((elt, edge))
        # scanArchiveFilePrefix = "_".join((scanArchiveFilePrefix, symbol))

        # i = 1
        # while os.path.isfile(os.path.extsep.join((scanArchiveFilePrefix + str(i), "raw"))):
        # i = i + 1

        # scanArchiveFilePrefix = scanArchiveFilePrefix + str(i)
        # archiveRawScanFile=os.path.extsep.join((scanArchiveFilePrefix, "raw"))
        rawScanFile = os.path.extsep.join((scanFilePrefix, "raw"))
        scanFile = os.path.extsep.join((scanFilePrefix, "efs"))
        logging.info(
            "SOLEILEnergyScan do_chooch rawScanFile %s, scanFile %s"
            % (rawScanFile, scanFile)
        )
        # if not os.path.exists(os.path.dirname(scanArchiveFilePrefix)):
        # os.makedirs(os.path.dirname(scanArchiveFilePrefix))

        # try:
        # f=open(rawScanFile, "w")
        # pyarch_f=open(archiveRawScanFile, "w")
        # except:
        # logging.getLogger("HWR").exception("could not create raw scan files")
        # self.storeEnergyScan()
        # self.emit("energyScanFailed", ())
        # return
        # else:
        # scanData = []

        # if scanObject is None:
        # raw_data_file = os.path.join(os.path.dirname(scanFilePrefix), 'data.raw')
        # try:
        # raw_file = open(raw_data_file, 'r')
        # except:
        # self.storeEnergyScan()
        # self.emit("energyScanFailed", ())
        # return

        # for line in raw_file.readlines()[2:]:
        # (x, y) = line.split('\t')
        # x = float(x.strip())
        # y = float(y.strip())
        # x = x < 1000 and x*1000.0 or x
        # scanData.append((x, y))
        # f.write("%f,%f\r\n" % (x, y))
        # pyarch_f.write("%f,%f\r\n"% (x, y))
        # else:
        # for i in range(len(scanObject.x)):
        # x = float(scanObject.x[i])
        # x = x < 1000 and x*1000.0 or x
        # y = float(scanObject.y[i])
        # scanData.append((x, y))
        # f.write("%f,%f\r\n" % (x, y))
        # pyarch_f.write("%f,%f\r\n"% (x, y))

        # f.close()
        # pyarch_f.close()
        # self.scanInfo["scanFileFullPath"]=str(archiveRawScanFile)
        scanData = self.xanes.raw
        logging.info("scanData %s" % scanData)
        logging.info("PyChooch file %s" % PyChooch.__file__)
        pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = PyChooch.calc(
            scanData, elt, edge, scanFile
        )
        rm = (pk + 30) / 1000.0
        pk = pk / 1000.0
        savpk = pk
        ip = ip / 1000.0
        comm = ""

        self.thEdge = self.xanes.e_edge
        logging.getLogger("HWR").info(
            "th. Edge %s ; chooch results are pk=%f, ip=%f, rm=%f"
            % (self.thEdge, pk, ip, rm)
        )
        logging.info("math.fabs(self.thEdge - ip) %s" % math.fabs(self.thEdge - ip))
        logging.info("self.thEdgeThreshold %s" % self.thEdgeThreshold)

        logging.getLogger("HWR").warning(
            "EnergyScan: calculated peak (%f) is more that 20eV %s the theoretical value (%f). Please check your scan and choose the energies manually"
            % (
                savpk,
                (self.thEdge - ip) < self.thEdgeThreshold and "below" or "above",
                self.thEdge,
            )
        )

        if math.fabs(self.thEdge - ip) > self.thEdgeThreshold:
            logging.info("Theoretical edge too different from the one just determined")
            pk = 0
            ip = 0
            rm = self.thEdge + 0.03
            comm = (
                "Calculated peak (%f) is more that 10eV away from the theoretical value (%f). Please check your scan"
                % (savpk, self.thEdge)
            )

            logging.getLogger("HWR").warning(
                "EnergyScan: calculated peak (%f) is more that 20eV %s the theoretical value (%f). Please check your scan and choose the energies manually"
                % (
                    savpk,
                    (self.thEdge - ip) < self.thEdgeThreshold and "below" or "above",
                    self.thEdge,
                )
            )

        archiveEfsFile = os.path.extsep.join((scanArchiveFilePrefix, "efs"))

        logging.info("archiveEfsFile %s" % archiveEfsFile)

        # Check access to archive directory
        dirname = os.path.dirname(archiveEfsFile)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
                logging.getLogger("user_level_log").info(
                    "Chooch. Archive path (%s) created" % dirname
                )
            except OSError:
                logging.getLogger("user_level_log").error(
                    "Chooch. Archive path is not accessible (%s)" % dirname
                )
                return None
            except Exception:
                import traceback

                logging.getLogger("user_level_log").error(
                    "Error creating archive path (%s) \n   %s"
                    % (dirname, traceback.format_exc())
                )
                return None
        else:
            if not os.path.isdir(dirname):
                logging.getLogger("user_level_log").error(
                    "Chooch. Archive path does not seem to be a valid directory (%s)"
                    % dirname
                )
                return None

        try:
            fi = open(scanFile)
            fo = open(archiveEfsFile, "w")
        except Exception:
            import traceback

            logging.getLogger("user_level_log").error(traceback.format_exc())
            self.storeEnergyScan()
            self.emit("energyScanFailed", ())
            return None
        else:
            fo.write(fi.read())
            fi.close()
            fo.close()

        logging.info("archive saved")
        self.scanInfo["peakEnergy"] = pk
        self.scanInfo["inflectionEnergy"] = ip
        self.scanInfo["remoteEnergy"] = rm
        self.scanInfo["peakFPrime"] = fpPeak
        self.scanInfo["peakFDoublePrime"] = fppPeak
        self.scanInfo["inflectionFPrime"] = fpInfl
        self.scanInfo["inflectionFDoublePrime"] = fppInfl
        self.scanInfo["comments"] = comm
        logging.info("self.scanInfo %s" % self.scanInfo)

        logging.info("chooch_graph_data %s" % str(chooch_graph_data))
        chooch_graph_x, chooch_graph_y1, chooch_graph_y2 = zip(*chooch_graph_data)
        chooch_graph_x = list(chooch_graph_x)
        logging.info("chooch_graph_x %s" % str(chooch_graph_x))
        for i in range(len(chooch_graph_x)):
            chooch_graph_x[i] = chooch_graph_x[i] / 1000.0

        logging.getLogger("HWR").info("<chooch> Saving png")
        # prepare to save png files
        title = "%10s  %6s  %6s\n%10s  %6.2f  %6.2f\n%10s  %6.2f  %6.2f" % (
            "energy",
            "f'",
            "f''",
            pk,
            fpPeak,
            fppPeak,
            ip,
            fpInfl,
            fppInfl,
        )
        fig = Figure(figsize=(15, 11))
        ax = fig.add_subplot(211)
        ax.set_title("%s\n%s" % (scanFile, title))
        ax.grid(True)
        ax.plot(*(zip(*scanData)), **{"color": "black"})
        ax.set_xlabel("Energy")
        ax.set_ylabel("MCA counts")
        ax2 = fig.add_subplot(212)
        ax2.grid(True)
        ax2.set_xlabel("Energy")
        ax2.set_ylabel("")
        handles = []
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y1, color="blue"))
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y2, color="red"))
        canvas = FigureCanvasAgg(fig)

        escan_png = os.path.extsep.join((scanFilePrefix, "png"))
        escan_archivepng = os.path.extsep.join((scanArchiveFilePrefix, "png"))
        self.scanInfo["jpegChoochFileFullPath"] = str(escan_archivepng)
        try:
            logging.getLogger("HWR").info(
                "Rendering energy scan and Chooch graphs to PNG file : %s", escan_png
            )
            canvas.print_figure(escan_png, dpi=80)
        except Exception:
            logging.getLogger("HWR").exception("could not print figure")
        try:
            logging.getLogger("HWR").info(
                "Saving energy scan to archive directory for ISPyB : %s",
                escan_archivepng,
            )
            canvas.print_figure(escan_archivepng, dpi=80)
        except Exception:
            logging.getLogger("HWR").exception("could not save figure")

        self.storeEnergyScan()
        self.scanInfo = None

        logging.getLogger("HWR").info("<chooch> returning")
        self.emit(
            "chooch_finished",
            (
                pk,
                fppPeak,
                fpPeak,
                ip,
                fppInfl,
                fpInfl,
                rm,
                chooch_graph_x,
                chooch_graph_y1,
                chooch_graph_y2,
                title,
            ),
        )
        self.choochResults = (
            pk,
            fppPeak,
            fpPeak,
            ip,
            fppInfl,
            fpInfl,
            rm,
            chooch_graph_x,
            chooch_graph_y1,
            chooch_graph_y2,
            title,
        )
        return (
            pk,
            fppPeak,
            fpPeak,
            ip,
            fppInfl,
            fpInfl,
            rm,
            chooch_graph_x,
            chooch_graph_y1,
            chooch_graph_y2,
            title,
        )

    def scanStatusChanged(self, status):
        self.emit("scanStatusChanged", (status,))

    def storeEnergyScan(self):
        # self.xanes.saveDat()
        self.xanes.saveRaw()
        self.xanes.saveResults()

        # if HWR.beamline.lims is None:
        # return
        # try:
        # session_id=int(self.scanInfo['sessionId'])
        # except:
        # return
        # gevent.spawn(StoreEnergyScanThread, HWR.beamline.lims,self.scanInfo)
        logging.info("SOLEILEnergyScan storeEnergyScan OK")
        # self.storeScanThread.start()

    def updateEnergyScan(self, scan_id, jpeg_scan_filename):
        pass

    # Move energy commands

    def get_current_energy(self):
        if HWR.beamline.energy is not None:
            try:
                return HWR.beamline.energy.get_value()
            except Exception:
                logging.getLogger("HWR").exception("EnergyScan: couldn't read energy")
                return None
        elif (
            self.energy2WavelengthConstant is not None
            and self.defaultWavelength is not None
        ):
            return self.energy2wavelength(self.defaultWavelength)

        return None

    def get_value(self):
        return self.get_current_energy()

    def getEnergyLimits(self):
        lims = None
        if HWR.beamline.energy is not None:
            if HWR.beamline.energy.is_ready():
                lims = HWR.beamline.energy.get_limits()
        return lims

    def get_wavelength(self):
        if HWR.beamline.energy is not None:
            try:
                return self.energy2wavelength(HWR.beamline.energy.get_value())
            except Exception:
                logging.getLogger("HWR").exception("EnergyScan: couldn't read energy")
                return None
        else:
            return self.defaultWavelength

    def getWavelengthLimits(self):
        limits = None
        if HWR.beamline.energy is not None:
            if HWR.beamline.energy.is_ready():
                limits = HWR.beamline.energy.get_wavelength_limits()
        return limits

    def startMoveEnergy(self, value, wait=True):
        logging.getLogger("HWR").info("Moving energy to (%s)" % value)
        try:
            value = float(value)
        except (TypeError, ValueError) as diag:
            logging.getLogger("HWR").error("EnergyScan: invalid energy (%s)" % value)
            return False

        try:
            curr_energy = HWR.beamline.energy.get_value()
        except Exception:
            logging.getLogger("HWR").exception(
                "EnergyScan: couldn't get current energy"
            )
            curr_energy = None

        if value != curr_energy:
            logging.getLogger("HWR").info("Moving energy: checking limits")
            try:
                lims = HWR.beamline.energy.get_limits()
            except Exception:
                logging.getLogger("HWR").exception(
                    "EnergyScan: couldn't get energy limits"
                )
                in_limits = False
            else:
                in_limits = value >= lims[0] and value <= lims[1]

            if in_limits:
                logging.getLogger("HWR").info("Moving energy: limits ok")
                self.previousResolution = None
                if HWR.beamline.resolution is not None:
                    try:
                        self.previousResolution = HWR.beamline.resolution.get_value()
                    except Exception:
                        logging.getLogger("HWR").exception(
                            "EnergyScan: couldn't get current resolution"
                        )
                self.moveEnergyCmdStarted()

                def change_egy():
                    try:
                        self.moveEnergy(value, wait=True)
                    except Exception:
                        self.moveEnergyCmdFailed()
                    else:
                        self.moveEnergyCmdFinished(True)

                if wait:
                    change_egy()
                else:
                    gevent.spawn(change_egy)
            else:
                logging.getLogger("HWR").error(
                    "EnergyScan: energy (%f) out of limits (%s)" % (value, lims)
                )
                return False
        else:
            return None

        return True

    def set_wavelength(self, value, wait=True):
        energy_val = self.energy2wavelength(value)
        if energy_val is None:
            logging.getLogger("HWR").error(
                "EnergyScan: unable to convert wavelength to energy"
            )
            return False
        return self.startMoveEnergy(energy_val, wait)

    def cancelMoveEnergy(self):
        self.moveEnergy.abort()

    def energy2wavelength(self, val):
        if self.energy2WavelengthConstant is None:
            return None
        try:
            other_val = self.energy2WavelengthConstant / val
        except ZeroDivisionError:
            other_val = None
        return other_val

    def energyPositionChanged(self, pos):
        wav = self.energy2wavelength(pos)
        if wav is not None:
            self.emit("energyChanged", (pos, wav))
            self.emit("valueChanged", (pos,))

    def energyLimitsChanged(self, limits):
        self.emit("energyLimitsChanged", (limits,))
        wav_limits = (
            self.energy2wavelength(limits[1]),
            self.energy2wavelength(limits[0]),
        )
        if wav_limits[0] is not None and wav_limits[1] is not None:
            self.emit("wavelengthLimitsChanged", (wav_limits,))
        else:
            self.emit("wavelengthLimitsChanged", (None,))

    def moveEnergyCmdReady(self):
        if not self.moving:
            self.emit("moveEnergyReady", (True,))

    def moveEnergyCmdNotReady(self):
        if not self.moving:
            self.emit("moveEnergyReady", (False,))

    def moveEnergyCmdStarted(self):
        self.moving = True
        self.emit("moveEnergyStarted", ())

    def moveEnergyCmdFailed(self):
        self.moving = False
        self.emit("moveEnergyFailed", ())

    def moveEnergyCmdAborted(self):
        pass
        # self.moving = False
        # self.emit('moveEnergyFailed', ())

    def moveEnergyCmdFinished(self, result):
        self.moving = False
        self.emit("moveEnergyFinished", ())

    def getPreviousResolution(self):
        return (self.previousResolution, self.lastResolution)

    def restoreResolution(self):
        if HWR.beamline.resolution is not None:
            if self.previousResolution is not None:
                try:
                    HWR.beamline.resolution.set_value(self.previousResolution)
                except Exception:
                    return (False, "Error trying to move the detector")
                else:
                    return (True, None)
            else:
                return (False, "Unknown previous resolution")
        else:
            return (False, "Resolution motor not defined")

    # Elements commands
    def get_elements(self):
        elements = []
        try:
            for el in self["elements"]:
                elements.append({"symbol": el.symbol, "energy": el.energy})
        except IndexError:
            pass
        return elements

    # # Mad energies commands
    # def getDefaultMadEnergies(self):
    #     energies = []
    #     try:
    #         for el in self["mad"]:
    #             energies.append([float(el.energy), el.directory])
    #     except IndexError:
    #         pass
    #     return energies


def StoreEnergyScanThread(db_conn, scan_info):
    return
    scanInfo = dict(scan_info)
    dbConnection = db_conn

    blsampleid = scanInfo["blSampleId"]
    scanInfo.pop("blSampleId")
    db_status = dbConnection.storeEnergyScan(scanInfo)
    if blsampleid is not None:
        try:
            energyscanid = int(db_status["energyScanId"])
        except Exception:
            pass
        else:
            asoc = {"blSampleId": blsampleid, "energyScanId": energyscanid}
            dbConnection.associateBLSampleAndEnergyScan(asoc)
