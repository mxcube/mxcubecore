from qt import copy
import logging
import os
import time
import gevent.event
import gevent
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository import HardwareRepository as HWR


class XrfSpectrum(Equipment):
    def init(self):

        self.scanning = None
        self.moving = None
        self.ready_event = gevent.event.Event()

        try:
            self.config_data = self.get_channel_object("config_data")
        except Exception:
            self.config_data = None

        try:
            self.calib_data = self.get_channel_object(" calib_data")
        except Exception:
            self.calib_data = None

        try:
            self.energySpectrumArgs = self.get_channel_object("spectrum_args")
        except KeyError:
            logging.getLogger().warning(
                "XRFSpectrum: error initializing energy spectrum arguments (missing channel)"
            )
            self.energySpectrumArgs = None

        try:
            self.spectrumStatusMessage = self.get_channel_object("spectrumStatusMsg")
        except KeyError:
            self.spectrumStatusMessage = None
            logging.getLogger().warning(
                "XRFSpectrum: energy messages will not appear (missing channel)"
            )
        else:
            self.spectrumStatusMessage.connectSignal(
                "update", self.spectrumStatusChanged
            )

        try:
            self.doSpectrum.connectSignal(
                "commandBeginWaitReply", self.spectrumCommandStarted
            )
            self.doSpectrum.connectSignal("commandFailed", self.spectrumCommandFailed)
            self.doSpectrum.connectSignal("commandAborted", self.spectrumCommandAborted)
            self.doSpectrum.connectSignal("commandReady", self.spectrumCommandReady)
            self.doSpectrum.connectSignal(
                "commandNotReady", self.spectrumCommandNotReady
            )
        except AttributeError as diag:
            logging.getLogger().warning(
                "XRFSpectrum: error initializing energy spectrum (%s)" % str(diag)
            )
            self.doSpectrum = None
        else:
            self.doSpectrum.connectSignal("connected", self.sConnected)
            self.doSpectrum.connectSignal("disconnected", self.sDisconnected)

        if HWR.beamline.lims is None:
            logging.getLogger().warning(
                "XRFSpectrum: you should specify the database hardware object"
            )
        self.spectrumInfo = None

        try:
            self.ctrl_hwobj = self.getObjectByRole("controller")
        except Exception:
            self.ctrl_hwobj = None

        try:
            self.mca_hwobj = self.getObjectByRole("mca")
            # self.mca_hwobj.set_calibration(calib_cf=[0,0.008324,2.223e-06])
            self.mca_hwobj.set_calibration(calib_cf=self.mca_hwobj.calib_cf)
        except Exception:
            self.mca_hwobj = None

        try:
            self.datapath = self.getProperty("datapath")
        except Exception:
            self.datapath = "/data/pyarch/"

        try:
            self.cfgpath = self.getProperty("cfgpath")
        except Exception:
            self.cfgpath = "/users/blissadm/local/userconf"

        if self.isConnected():
            self.sConnected()

    def isConnected(self):
        try:
            return self.doSpectrum.isConnected()
        except Exception:
            return False

    # Handler for spec connection
    def sConnected(self):
        self.emit("connected", ())
        # curr = self.getSpectrumParams()

    # Handler for spec disconnection
    def sDisconnected(self):
        self.emit("disconnected", ())

    # Energy spectrum commands
    def canSpectrum(self):
        if not self.isConnected():
            return False
        return self.doSpectrum is not None

    def startXrfSpectrum(
        self, ct, directory, prefix, session_id=None, blsample_id=None
    ):
        self.spectrumInfo = {"sessionId": session_id, "blSampleId": blsample_id}
        self.spectrumCommandStarted()
        if not os.path.isdir(directory):
            logging.getLogger().debug("XRFSpectrum: creating directory %s" % directory)
            try:
                os.makedirs(directory)
            except OSError as diag:
                logging.getLogger().error(
                    "XRFSpectrum: error creating directory %s (%s)"
                    % (directory, str(diag))
                )
                self.spectrumStatusChanged("Error creating directory")
                return False

        curr = self.getSpectrumParams()

        try:
            curr["escan_dir"] = directory
            curr["escan_prefix"] = prefix
        except TypeError:
            curr = {}
            curr["escan_dir"] = directory
            curr["escan_prefix"] = prefix

        a = directory.split(os.path.sep)
        suffix_path = os.path.join(*a[4:])
        if "inhouse" in a:
            a_dir = os.path.join(self.datapath, a[2], suffix_path)
        else:
            a_dir = os.path.join(self.datapath, a[4], a[3], *a[5:])
        if a_dir[-1] != os.path.sep:
            a_dir += os.path.sep
        if not os.path.exists(a_dir):
            try:
                # logging.getLogger().debug("XRFSpectrum: creating %s", a_dir)
                os.makedirs(a_dir)
            except OSError as diag:
                logging.getLogger().error(
                    "XRFSpectrum: error creating directory %s (%s)" % (a_dir, str(diag))
                )
                self.spectrumStatusChanged("Error creating directory")
                return False

        filename_pattern = os.path.join(
            directory, "%s_%s_%%02d" % (prefix, time.strftime("%d_%b_%Y"))
        )
        aname_pattern = os.path.join(
            "%s/%s_%s_%%02d" % (a_dir, prefix, time.strftime("%d_%b_%Y"))
        )

        filename_pattern = os.path.extsep.join((filename_pattern, "dat"))
        html_pattern = os.path.extsep.join((aname_pattern, "html"))
        aname_pattern = os.path.extsep.join((aname_pattern, "png"))
        filename = filename_pattern % 1
        aname = aname_pattern % 1
        htmlname = html_pattern % 1

        i = 2
        while os.path.isfile(filename):
            filename = filename_pattern % i
            aname = aname_pattern % i
            htmlname = html_pattern % i
            i = i + 1

        self.spectrumInfo["filename"] = filename
        # self.spectrumInfo["scanFileFullPath"] = filename
        self.spectrumInfo["jpegScanFileFullPath"] = aname
        self.spectrumInfo["exposureTime"] = ct
        self.spectrumInfo["annotatedPymcaXfeSpectrum"] = htmlname
        logging.getLogger().debug("XRFSpectrum: archive file is %s", aname)

        gevent.spawn(self.reallyStartXrfSpectrum, ct, filename)

        return True

    def reallyStartXrfSpectrum(self, ct, filename):

        if self.doSpectrum:
            try:
                res = self.doSpectrum(ct, filename, wait=True)
            except Exception:
                logging.getLogger().exception("XRFSpectrum: problem calling spec macro")
                self.spectrumStatusChanged("Error problem spec macro")
            else:
                self.spectrumCommandFinished(res)
        else:
            try:
                res = self._doSpectrum(ct, filename, wait=True)
            except Exception:
                logging.getLogger().exception("XRFSpectrum: problem calling procedure")
                self.spectrumStatusChanged("Error problem with spectrum procedure")
            else:
                self.spectrumCommandFinished(res)

    def cancelXrfSpectrum(self, *args):
        if self.scanning:
            self.doSpectrum.abort()

    def spectrumCommandReady(self):
        if not self.scanning:
            self.emit("xrfSpectrumReady", (True,))
            self.emit("xrfScanReady", (True,))

    def spectrumCommandNotReady(self):
        if not self.scanning:
            self.emit("xrfSpectrumReady", (False,))
            self.emit("xrfScanReady", (False,))

    def spectrumCommandStarted(self, *args):
        self.spectrumInfo["startTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit("xrfSpectrumStarted", ())
        self.emit("xrfScanStarted", ())

    def spectrumCommandFailed(self, *args):
        self.spectrumInfo["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.storeXrfSpectrum()
        self.emit("xrfSpectrumFailed", ())
        self.emit("xrfScanFailed", ())
        self.ready_event.set()

    def spectrumCommandAborted(self, *args):
        self.scanning = False
        self.emit("xrfSpectrumFailed", ())
        self.emit("xrfScanFailed", ())
        self.ready_event.set()

    def spectrumCommandFinished(self, result):
        self.spectrumInfo["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        logging.getLogger().debug("XRFSpectrum: XRF spectrum result is %s" % result)
        self.scanning = False

        if result:
            try:
                mcaData = self.get_channel_object("mca_data").getValue()
                mcaCalib = self.get_channel_object("calib_data").getValue()
            except Exception:
                mcaData = self.mca_hwobj.read_data(save_data=True)
                mcaCalib = self.mca_hwobj.get_calibration()
            try:
                mcaConfig = self.get_channel_object("config_data").getValue()
                self.spectrumInfo["beamTransmission"] = mcaConfig["att"]
                self.spectrumInfo["energy"] = mcaConfig["energy"]
                self.spectrumInfo["beamSizeHorizontal"] = float(mcaConfig["bsX"])
                self.spectrumInfo["beamSizeVertical"] = float(mcaConfig["bsY"])
            except Exception:
                mcaConfig = {}
                # self.spectrumInfo["beamTransmission"] =  self.transmission_hwobj.get_value()
                self.spectrumInfo["energy"] = HWR.beamline.energy.get_value()
                beam_info = HWR.beamline.beam.get_beam_info()
                self.spectrumInfo["beamSizeHorizontal"] = beam_info["size_x"]
                self.spectrumInfo["beamSizeVertical"] = beam_info["size_y"]
                mcaConfig["att"] = self.spectrumInfo["beamTransmission"]
                mcaConfig["energy"] = self.spectrumInfo["energy"]
                mcaConfig["bsX"] = self.spectrumInfo["beamSizeHorizontal"]
                mcaConfig["bsY"] = self.spectrumInfo["beamSizeVertical"]
                roi = self.mca_hwobj.get_roi()
                mcaConfig["min"] = roi["chmin"]
                mcaConfig["max"] = roi["chmax"]
            mcaConfig["legend"] = self.spectrumInfo["annotatedPymcaXfeSpectrum"]
            mcaConfig["htmldir"], _ = os.path.split(mcaConfig["legend"])
            mcaConfig["file"] = self._get_cfgfile(self.spectrumInfo["energy"])

            # here move the png file
            pf = self.spectrumInfo["filename"].split(".")
            pngfile = os.path.extsep.join((pf[0], "png"))
            if os.path.isfile(pngfile) is True:
                try:
                    copy(pngfile, self.spectrumInfo["jpegScanFileFullPath"])
                except Exception:
                    logging.getLogger().error("XRFSpectrum: cannot copy %s", pngfile)

            logging.getLogger().debug("finished %r", self.spectrumInfo)
            self.storeXrfSpectrum()
            # self.emit('xrfSpectrumFinished', (mcaData,mcaCalib,mcaConfig))
            self.emit("xrfScanFinished", (mcaData, mcaCalib, mcaConfig))
        else:
            self.spectrumCommandFailed()
        self.ready_event.set()

    def spectrumStatusChanged(self, status):
        self.emit("xrfScanStatusChanged", (status,))
        self.emit("spectrumStatusChanged", (status,))

    def storeXrfSpectrum(self):
        logging.getLogger().debug("db connection %r", HWR.beamline.lims)
        logging.getLogger().debug("spectrum info %r", self.spectrumInfo)
        if HWR.beamline.lims is None:
            return
        try:
            int(self.spectrumInfo["sessionId"])
        except Exception:
            return
        self.spectrumInfo["blSampleId"]
        self.spectrumInfo.pop("blSampleId")

        HWR.beamline.lims.storeXfeSpectrum(self.spectrumInfo)

    def updateXrfSpectrum(self, spectrum_id, jpeg_spectrum_filename):
        pass

    def getSpectrumParams(self):
        if self.energySpectrumArgs:
            try:
                self.curr = self.energySpectrumArgs.getValue()
                return self.curr
            except Exception:
                logging.getLogger().exception(
                    "XRFSpectrum: error getting xrfspectrum parameters"
                )
                self.spectrumStatusChanged("Error getting xrfspectrum parameters")
                return False
        else:
            return True

    def setSpectrumParams(self, pars):
        self.energySpectrumArgs.setValue(pars)

    def _get_cfgfile(self, energy):
        if energy > 12.0:
            cfgname = "15"
        elif energy > 10.0:
            cfgname = "12"
        elif energy > 7.0:
            cfgname = "10"
        else:
            cfgname = "7"
        return os.path.join(self.cfgpath, "%skeV.cfg" % cfgname)

    def _doSpectrum(self, ct, filename, wait=True):
        HWR.beamline.energy.get_value()
        if not ct:
            ct = 5
        safshut = HWR.beamline.safety_shutter
        # stop the procedure if hutch not searched
        stat = safshut.getShutterState()
        if stat == "disabled":
            logging.getLogger("user_level_log").exception(
                "XRFSpectrum: hutch not searched, exiting"
            )
            return False

        fluodet_ctrl = self.getObjectByRole("fluodet_ctrl")
        fluodet_ctrl.actuatorIn()
        # open the safety and the fast shutter
        safshut.openShutter()
        init_transm = HWR.beamline.transmission.get_value()
        ret = self._findAttenuation(ct)
        self.ctrl_hwobj.diffractometer.msclose()
        fluodet_ctrl.actuatorOut()
        HWR.beamline.transmission.set_value(init_transm)
        return ret

    def _findAttenuation(self, ct):
        tf = [0.1, 0.2, 0.3, 0.9, 1.3, 1.9, 2.6, 4.3, 6, 8, 12, 24, 36, 50, 71]
        min_cnt = self.getProperty("min_cnt")
        max_cnt = self.getProperty("max_cnt")
        self.mca_hwobj.set_roi(2, 15, channel=1)
        print(self.spectrumInfo["filename"])
        self.mca_hwobj.set_presets(
            erange=1, ctime=ct, fname=self.spectrumInfo["filename"]
        )

        # put in max attenuation
        HWR.beamline.transmission.set_value(0)

        self.ctrl_hwobj.diffractometer.msopen()
        self.mca_hwobj.start_acq()
        time.sleep(ct)
        ic = sum(self.mca_hwobj.read_roi_data()) / ct
        print(ic)
        if ic > max_cnt:
            self.ctrl_hwobj.diffractometer.msclose()
            logging.getLogger("user_level_log").exception(
                "The detector is saturated, giving up."
            )
            return False
        for i in tf:
            self.mca_hwobj.clear_spectrum()
            logging.getLogger("user_level_log").info("Setting transmission to %g" % i)
            HWR.beamline.transmission.set_value(i)
            self.mca_hwobj.start_acq()
            time.sleep(ct)
            ic = sum(self.mca_hwobj.read_roi_data()) / ct
            print(ic)
            if ic > min_cnt:
                self.ctrl_hwobj.diffractometer.msclose()
                self.spectrumInfo[
                    "beamTransmission"
                ] = HWR.beamline.transmission.get_value()
                logging.getLogger("user_level_log").info(
                    "Transmission used for spectra: %g"
                    % self.spectrumInfo["beamTransmission"]
                )
                break
        self.ctrl_hwobj.diffractometer.msclose()
        if ic < min_cnt:
            logging.getLogger("user_level_log").exception(
                "Could not find satisfactory attenuation (is the mca properly set up?), giving up."
            )
            return False
        return True
