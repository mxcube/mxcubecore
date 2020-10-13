import logging
import os
import shutil
import time
import gevent.event
import gevent
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository import HardwareRepository as HWR


class XRFSpectrum(Equipment):
    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        self.scanning = None
        self.ready_event = gevent.event.Event()

        self.config_data = self.get_channel_object("config_data")
        self.calib_data = self.get_channel_object("calib_data")

        try:
            self.energySpectrumArgs = self.get_channel_object("spectrum_args")
        except KeyError:
            logging.getLogger().warning(
                "XRFSpectrum: error initializing energy spectrum arguments (missing channel)"
            )
            self.energySpectrumArgs = None

        try:
            self.doSpectrum.connect_signal(
                "commandBeginWaitReply", self.spectrumCommandStarted
            )
            self.doSpectrum.connect_signal("commandFailed", self.spectrumCommandFailed)
            self.doSpectrum.connect_signal(
                "commandAborted", self.spectrumCommandAborted
            )
            self.doSpectrum.connect_signal("commandReady", self.spectrumCommandReady)
            self.doSpectrum.connect_signal(
                "commandNotReady", self.spectrumCommandNotReady
            )
        except AttributeError as diag:
            logging.getLogger().warning(
                "XRFSpectrum: error initializing XRF spectrum (%s), probably not using SPEC macros"
                % str(diag)
            )
            self.doSpectrum = None
        else:
            self.doSpectrum.connect_signal("connected", self.sConnected)
            self.doSpectrum.connect_signal("disconnected", self.sDisconnected)

        if HWR.beamline.lims is None:
            logging.getLogger().warning(
                "XRFSpectrum: you should specify the database hardware object"
            )
        self.spectrumInfo = None

        self.ctrl_hwobj = self.get_object_by_role("controller")
        self.mca_hwobj = self.get_object_by_role("mca")
        # if self.mca_hwobj:
        #    self.mca_hwobj.set_calibration(calib_cf=self.mca_hwobj.calib_cf)

        self.archive_path = self.get_property("archive_path")
        if not self.archive_path:
            self.archive_path = "/data/pyarch/"

        self.cfg_path = self.get_property("cfg_path")
        if not self.cfg_path:
            self.cfg_path = "/users/blissadm/local/beamline_configuration/misc"

        if self.is_connected():
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
        if not self.is_connected():
            return False
        return self.doSpectrum is not None

    def startXrfSpectrum(
        self,
        ct,
        directory,
        archive_directory,
        prefix,
        session_id=None,
        blsample_id=None,
    ):
        self.spectrumInfo = {"sessionId": session_id, "blSampleId": blsample_id}
        self.spectrumCommandStarted()
        if not os.path.isdir(directory):
            logging.getLogger("user_level_log").debug(
                "XRFSpectrum: creating directory %s", directory
            )
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

        if not archive_directory:
            a = directory.split(os.path.sep)
            suffix_path = os.path.join(*a[4:])
            if "inhouse" in a:
                archive_directory = os.path.join(self.archive_path, a[2], suffix_path)
            else:
                archive_directory = os.path.join(self.archive_path, a[4], a[3], *a[5:])

        if not os.path.exists(archive_directory):
            try:
                logging.getLogger("user_level_log").debug(
                    "XRFSpectrum: creating %s", archive_directory
                )
                os.makedirs(archive_directory)
            except OSError as diag:
                logging.getLogger().error(
                    "XRFSpectrum: error creating directory %s (%s)",
                    (archive_directory, str(diag)),
                )
                self.spectrumStatusChanged("Error creating directory")
                return False

        _pattern = "%s_%s_%%02d" % (prefix, time.strftime("%d_%b_%Y"))
        filename_pattern = os.path.join(directory, _pattern)

        filename_pattern = os.path.extsep.join((filename_pattern, "dat"))
        filename = filename_pattern % 1
        fileprefix = _pattern % 1

        i = 2
        while os.path.isfile(filename):
            filename = filename_pattern % i
            fileprefix = _pattern % i
            i = i + 1

        archive_path = os.path.join(archive_directory, fileprefix)
        self.spectrumInfo["filename"] = filename
        self.spectrumInfo["scanFileFullPath"] = os.path.extsep.join(
            (archive_path, "dat")
        )
        self.spectrumInfo["jpegScanFileFullPath"] = os.path.extsep.join(
            (archive_path, "png")
        )
        self.spectrumInfo["annotatedPymcaXfeSpectrum"] = os.path.extsep.join(
            (archive_path, "html")
        )
        self.spectrumInfo["fittedDataFileFullPath"] = archive_path + "_peaks.csv"
        self.spectrumInfo["exposureTime"] = ct

        logging.getLogger("user_level_log").debug(
            "XRFSpectrum: archive file is %s", self.spectrumInfo["jpegScanFileFullPath"]
        )
        gevent.spawn(self.reallyStartXrfSpectrum, ct, filename)

        return True

    def reallyStartXrfSpectrum(self, ct, filename):
        try:
            res = self._doSpectrum(ct, filename, wait=True)
        except Exception:
            logging.getLogger("user_level_log").exception(
                "XRFSpectrum: problem calling procedure"
            )
            self.spectrumStatusChanged("Error problem with spectrum procedure")
        else:
            self.spectrumCommandFinished(res)

    def cancelXrfSpectrum(self, *args):
        if self.scanning:
            self.doSpectrum.abort()

    def spectrumCommandReady(self):
        if not self.scanning:
            self.emit("xrfSpectrumReady", (True,))
            # self.emit('xrfScanReady', (True,))

    def spectrumCommandNotReady(self):
        if not self.scanning:
            self.emit("xrfSpectrumReady", (False,))

    def spectrumCommandStarted(self, *args):
        self.spectrumInfo["startTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit("xrfSpectrumStarted", ())

    def spectrumCommandFailed(self, *args):
        self.spectrumInfo["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.storeXrfSpectrum()
        self.emit("xrfSpectrumFailed", ())
        self.ready_event.set()

    def spectrumCommandAborted(self, *args):
        self.scanning = False
        self.emit("xrfSpectrumFailed", ())
        self.ready_event.set()

    def spectrumCommandFinished(self, result):
        self.spectrumInfo["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        logging.getLogger().debug("XRFSpectrum: XRF spectrum result is %s" % result)
        self.scanning = False
        if result is not False:
            fname = self.spectrumInfo["filename"].replace(".dat", ".raw")
            self.mca_hwobj.set_presets(fname=str(fname))
            mcaData = self.mca_hwobj.read_data(save_data=True)
            mcaCalib = self.mca_hwobj.get_calibration()

            mcaConfig = {}
            self.spectrumInfo[
                "beamTransmission"
            ] = HWR.beamline.transmission.get_value()
            self.spectrumInfo["energy"] = HWR.beamline.energy.get_value()
            if HWR.beamline.flux:
                self.spectrumInfo["flux"] = HWR.beamline.flux.get_value()
            self.beamsize = self.get_object_by_role("beamsize")
            if self.beamsize:
                bsX = self.beamsize.get_size(self.beamsize.get_value().name)
                self.spectrumInfo["beamSizeHorizontal"] = bsX
                self.spectrumInfo["beamSizeVertical"] = bsX
                mcaConfig["bsX"] = self.spectrumInfo["beamSizeHorizontal"]
                mcaConfig["bsY"] = self.spectrumInfo["beamSizeVertical"]
            mcaConfig["att"] = self.spectrumInfo["beamTransmission"]
            mcaConfig["energy"] = self.spectrumInfo["energy"]
            roi = self.mca_hwobj.get_roi()
            mcaConfig["min"] = roi["chmin"]
            mcaConfig["max"] = roi["chmax"]
            mcaConfig["legend"] = self.spectrumInfo["annotatedPymcaXfeSpectrum"]
            mcaConfig["htmldir"], _ = os.path.split(mcaConfig["legend"])
            mcaConfig["file"] = self._get_cfgfile(self.spectrumInfo["energy"])
            try:
                self.set_data(mcaData, mcaCalib, mcaConfig)
            except Exception:
                self.emit("xrfSpectrumFinished", (mcaData, mcaCalib, mcaConfig))

            # here move the png file
            pf = self.spectrumInfo["filename"].split(".")
            pngfile = os.path.extsep.join((pf[0], "png"))
            if os.path.isfile(pngfile) is True:
                try:
                    shutil.copyfile(pngfile, self.spectrumInfo["jpegScanFileFullPath"])
                except Exception:
                    logging.getLogger().error("XRFSpectrum: cannot copy %s", pngfile)

            # copy raw data file to the archive directory
            try:
                shutil.copyfile(fname, self.spectrumInfo["scanFileFullPath"])
            except Exception:
                logging.getLogger().error(
                    "XRFSpectrum: cannot copy %s", self.spectrumInfo["filename"]
                )

            logging.getLogger().debug("finished %r", self.spectrumInfo)
            self.storeXrfSpectrum()

            # copy csv file in the raw data directory
            try:
                ff = self.spectrumInfo["filename"].replace(".dat", "_peaks.csv")
                shutil.copyfile(self.spectrumInfo["fittedDataFileFullPath"], ff)
            except Exception:
                logging.getLogger().error("XRFSpectrum: cannot copy %s", ff)
        else:
            self.spectrumCommandFailed()
        self.ready_event.set()

    def spectrumStatusChanged(self, status):
        self.emit("xrfScanStatusChanged", (status,))
        self.emit("xrfSpectrumStatusChanged", (status,))

    def storeXrfSpectrum(self):
        logging.getLogger().debug("db connection %r", HWR.beamline.lims)
        logging.getLogger().debug("spectrum info %r", self.spectrumInfo)
        if HWR.beamline.lims is None:
            return
        try:
            session_id = int(self.spectrumInfo["sessionId"])
        except Exception:
            return
        blsampleid = self.spectrumInfo["blSampleId"]

        db_status = HWR.beamline.lims.storeXfeSpectrum(self.spectrumInfo)

    def updateXrfSpectrum(self, spectrum_id, jpeg_spectrum_filename):
        pass

    def getSpectrumParams(self):
        if self.energySpectrumArgs:
            try:
                self.curr = self.energySpectrumArgs.get_value()
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
        self.energySpectrumArgs.set_value(pars)

    def _get_cfgfile(self, energy):
        if energy > 12.0:
            cfgname = "15"
        elif energy > 10.0:
            cfgname = "12"
        elif energy > 7.0:
            cfgname = "10"
        else:
            cfgname = "7"
        return os.path.join(self.cfg_path, "%skeV.cfg" % cfgname)

    def _doSpectrum(self, ct, filename, wait=True):
        if not ct:
            ct = 5
        safshut = self.get_object_by_role("safety_shutter")

        # stop the procedure if hutch not searched
        stat = safshut.getShutterState()
        if stat == "disabled":
            logging.getLogger("user_level_log").exception(
                "XRFSpectrum: hutch not searched, exiting"
            )
            return False

        fluodet_ctrl = self.get_object_by_role("fluodet_ctrl")
        fluodet_ctrl.actuatorIn()
        # put the beamstop in
        try:
            self.ctrl_hwobj.diffractometer.set_phase("DataCollection", wait=True)
        except Exception:
            pass

        # open the safety and the fast shutter
        safshut.openShutter()
        init_transm = HWR.beamline.transmission.get_value()
        logging.getLogger("user_level_log").info(
            "Looking for maximum attenuation, please wait"
        )
        ret = self._findAttenuation(ct)
        self.ctrl_hwobj.diffractometer.msclose()
        fluodet_ctrl.actuatorOut()
        HWR.beamline.transmission.set_value(init_transm)
        return ret

    def _findAttenuation(self, ct):
        table = self.get_property("transmission_table")
        if table:
            tf = []
            for i in table.split(","):
                tf.append(float(i))
        else:
            tf = [0.1, 0.2, 0.3, 0.9, 1.3, 1.9, 2.6, 4.3, 6, 8, 12, 24, 36, 50]

        min_cnt = self.get_property("min_cnt")
        max_cnt = self.get_property("max_cnt")
        self.mca_hwobj.set_roi(2, 15, channel=1)
        fname = self.spectrumInfo["filename"].replace(".dat", ".raw")
        self.mca_hwobj.set_presets(erange=1, ctime=ct, fname=fname)

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

        self.spectrumInfo["beamTransmission"] = HWR.beamline.transmission.get_value()
        self.ctrl_hwobj.diffractometer.msclose()
        if ic < min_cnt:
            logging.getLogger("user_level_log").exception(
                "Could not find satisfactory attenuation (is the mca properly set up?), giving up."
            )
            return False

        return True
