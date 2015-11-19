"""
Descript. :
"""
import os
import logging
import time
import gevent
import numpy
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from AbstractXRFSpectrum import AbstractXRFSpectrum
from HardwareRepository.TaskUtils import cleanup
from HardwareRepository.BaseHardwareObjects import HardwareObject


class EMBLXRFSpectrum(AbstractXRFSpectrum, HardwareObject):
    """
    Descript. 
    """
    def __init__(self, name):
        """
        Descript. :
        """
        AbstractXRFSpectrum.__init__(self)
        HardwareObject.__init__(self, name)

        self.can_scan = None
        self.ready_event = None
        self.scanning = None
        self.spectrum_info = None

        self.energy_hwobj = None
        self.transmission_hwobj = None
        self.db_connection_hwobj = None
        self.beam_info_hwobj = None

        self.cmd_scan_start = None
        self.chan_scan_status = None
        self.chan_scan_consts = None

        self.config_filename = None

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()

        self.energy_hwobj = self.getObjectByRole("energy")

        self.transmission_hwobj = self.getObjectByRole("transmission")
        if self.transmission_hwobj is None:
            logging.getLogger("HWR").warning("EMBLXRFSpectrum: Transmission hwobj not defined")

        self.db_connection_hwobj = self.getObjectByRole("dbserver")
        if self.db_connection_hwobj is None:
            logging.getLogger().warning("EMBLXRFSpectrum: DB hwobj not defined")

        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        if self.beam_info_hwobj is None:
            logging.getLogger("HWR").warning("EMBLXRFSpectrum: Beam info hwobj not defined")

        self.cmd_scan_start = self.getCommandObject('cmdScanStart')
        self.cmd_adjust_transmission = self.getCommandObject('cmdAdjustTransmission')
        self.chan_scan_status = self.getChannelObject('chanScanStatus')
        if self.chan_scan_status is not None:
            self.chan_scan_status.connectSignal('update', self.scan_status_update)
        self.chan_scan_consts = self.getChannelObject('chanScanConsts')

        self.can_scan = True
        if self.isConnected():
            self.sConnected()

        self.config_filename = self.getProperty("configFile")

    def scan_status_update(self, status):
        """
        Descript. :
        """

        if self.scanning == True:
            if status == 'scanning':
                logging.getLogger("HWR").info('XRF scan in progress...')
            elif status == 'ready':
                if self.scanning:
                    self.spectrumCommandFinished()
                    logging.getLogger("HWR").info('XRF scan finished')
            elif status == 'aborting':
                if self.scanning:
                    self.spectrumCommandAborted()
                    logging.getLogger("HWR").info('XRF scan aborted!')
            elif status == 'error':
                self.spectrumCommandFailed()
                logging.getLogger("HWR").error('XRF scan error!')

    def isConnected(self):
        """
        Descript. :
        """
        return self.can_scan

    def sConnected(self):
        """
        Descript. :
        """
        self.emit('connected', ())

    def sDisconnected(self):
        """
        Descript. :
        """
        self.emit('disconnected', ())

    def canSpectrum(self):
        """
        Descript. :
        """
        return self.can_scan

    def startXrfSpectrum(self, ct, scan_directory, archive_directory, prefix,
            session_id = None, blsample_id = None, adjust_transmission = True):
        """
        Descript. :
        """
        if not self.can_scan:
            self.spectrumCommandAborted()
            return False

        self.spectrum_info = {"sessionId": session_id, "blSampleId": blsample_id}
        if not os.path.isdir(archive_directory):
            logging.getLogger().debug("EMBLXRFSpectrum: creating directory %s" % archive_directory)
            try:
                if not os.path.exists(archive_directory):
                    os.makedirs(archive_directory)
                if not os.path.exists(scan_directory):
                    os.makedirs(scan_directory)
            except OSError, diag:
                logging.getLogger().error("EMBLXRFSpectrum: error creating directory %s (%s)" % (archive_directory, str(diag)))
                self.emit('xrfScanStatusChanged', ("Error creating directory", ))
                self.spectrumCommandAborted()
                return False

        archive_file_template = os.path.join(archive_directory, prefix) 
        scan_file_template = os.path.join(scan_directory, prefix)
        if os.path.exists(archive_file_template + ".dat"):
            i = 1
            while os.path.exists(archive_file_template + "%d.dat" %i):
                  i = i + 1
            archive_file_template += "_%d" % i
            scan_file_template += "_%d" % i
            prefix += "_%d" % i

        scan_file_dat_filename = os.path.extsep.join((scan_file_template, "dat")) 
        archive_file_dat_filename = os.path.extsep.join((archive_file_template, "dat"))
        archive_file_png_filename = os.path.extsep.join((archive_file_template, "png"))
        archive_file_html_filename = os.path.extsep.join((archive_file_template, "html"))

        self.spectrum_info["filename"] = prefix
        self.spectrum_info["scanFilePath"] = scan_file_dat_filename
        self.spectrum_info["scanFileFullPath"] = archive_file_dat_filename
        self.spectrum_info["jpegScanFileFullPath"] = archive_file_png_filename
        self.spectrum_info["exposureTime"] = ct
        self.spectrum_info["annotatedPymcaXfeSpectrum"] = archive_file_html_filename
        self.spectrum_info["htmldir"] = archive_directory
        self.spectrumCommandStarted()
        logging.getLogger().debug("EMBLXRFSpectrum: scan dat file is %s", scan_file_dat_filename)
        logging.getLogger().debug("EMBLXRFSpectrum: archive file is %s", archive_file_dat_filename)

        try:
            self.cmd_scan_start((ct, adjust_transmission))
        except:
            logging.getLogger().exception('EMBLXRFSpectrum: problem in starting scan')
            self.emit('xrfScanStatusChanged', ("Error problem in starting scan",))
            self.spectrumCommandAborted()

    def cancelXrfSpectrum(self, *args):
        """
        Descript. :
        """
        if self.scanning:
            #self.doSpectrum.abort()
            self.ready_event.set()

    def spectrumCommandReady(self):
        """
        Descript. :
        """
        if not self.scanning:
            self.emit('xrfSpectrumReady', (True, ))

    def spectrumCommandNotReady(self):
        """
        Descript. :
        """
        if not self.scanning:
            self.emit('xrfSpectrumReady', (False, ))

    def spectrumCommandStarted(self, *args):
        """
        Descript. :
        """
        self.spectrum_info['startTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit('xrfScanStarted', ())

    def spectrumCommandFailed(self, *args):
        """
        Descript. :
        """
        self.spectrum_info['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.store_xrf_spectrum()
        self.emit('xrfScanFailed', ())
        self.ready_event.set()
    
    def spectrumCommandAborted(self, *args):
        """
        Descript. :
        """
        self.scanning = False
        self.emit('xrfScanFailed', ())
        self.ready_event.set()

    def spectrumCommandFinished(self):
        """
        Descript. :
        """
        with cleanup(self.ready_event.set):
            self.spectrum_info['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.scanning = False

            values = list(self.cmd_scan_start.get())

            xmin = 0
            xmax = 0
            mcaCalib = self.chan_scan_consts.getValue()[::-1]
            mcaData = []
            calibrated_data = []

            try:
               scan_file_raw = open(self.spectrum_info["scanFileFullPath"], "w")
               archive_file_raw = open(self.spectrum_info["scanFilePath"], "w")
            except:
               logging.getLogger("HWR").exception("EMBLXRFSpectrum: could not create spectrum result raw file %s" %self.spectrum_info["scanFileFullPath"])

            for n, value in enumerate(values):
                energy = (mcaCalib[2] + mcaCalib[1] * n + mcaCalib[0] * n * n) / 1000
                if energy < 13:
                    if energy > xmax:
                        xmax = value
                    if energy < xmin:
                        xmin = value
                    calibrated_data.append([energy, value])
                    mcaData.append((n / 1000.0, value))
                    if scan_file_raw:
                        scan_file_raw.write("%f,%f\r\n" % (energy, value))
                    if archive_file_raw:
                        archive_file_raw.write("%f,%f\r\n" % (energy, value)) 
            if scan_file_raw:
                scan_file_raw.close()
            if archive_file_raw:
                archive_file_raw.close()

            calibrated_array = numpy.array(calibrated_data)

            self.spectrum_info["beamTransmission"] = self.transmission_hwobj.getAttFactor()
            self.spectrum_info["energy"] = self.getCurrentEnergy()
            beam_size = self.beam_info_hwobj.get_beam_size()
            self.spectrum_info["beamSizeHorizontal"] = int(beam_size[0] * 1000)
            self.spectrum_info["beamSizeVertical"] = int(beam_size[1] * 1000)

            mcaConfig = {}
            mcaConfig["legend"] = self.spectrum_info["filename"]
            mcaConfig["file"] = self.config_filename
            mcaConfig["min"] = xmin
            mcaConfig["max"] = xmax
            mcaConfig["htmldir"] = self.spectrum_info["htmldir"]
            self.spectrum_info.pop("htmldir")
            self.spectrum_info.pop("scanFilePath")

            fig = Figure(figsize=(15, 11))
            ax = fig.add_subplot(111)
            ax.set_title(self.spectrum_info["jpegScanFileFullPath"])
            ax.grid(True)

            ax.plot(*(zip(*calibrated_array)), **{"color" : 'black'})
            ax.set_xlabel("Energy")
            ax.set_ylabel("Counts")
            canvas = FigureCanvasAgg(fig)
            logging.getLogger().info("Rendering spectrum to PNG file : %s", self.spectrum_info["jpegScanFileFullPath"])
            canvas.print_figure(self.spectrum_info["jpegScanFileFullPath"], dpi = 80)
            #logging.getLogger().debug("Copying .fit file to: %s", a_dir)
            #tmpname=filename.split(".")
            #logging.getLogger().debug("finished %r", self.spectrum_info)
            self.store_xrf_spectrum()
            self.emit('xrfScanFinished', (mcaData, mcaCalib, mcaConfig))
            
    def spectrumStatusChanged(self, status):
        """
        Descript. :
        """
        self.emit('xrfScanStatusChanged', (status, ))

    def store_xrf_spectrum(self):
        """
        Descript. :
        """
        #logging.getLogger().debug("db connection %r", self.db_connection_HO)
        #logging.getLogger().debug("spectrum info %r", self.spectrum_info)
        if self.db_connection_hwobj:
            try:
                session_id = int(self.spectrum_info['sessionId'])
            except:
                return
            blsampleid = self.spectrum_info['blSampleId']
            #self.spectrum_info.pop('blSampleId')
            db_status = self.db_connection_hwobj.storeXfeSpectrum(self.spectrum_info)

    def getCurrentEnergy(self):
        """
        Descript. :
        """
        if self.energy_hwobj is not None:
            try:
                return self.energy_hwobj.getCurrentEnergy()
            except:
                logging.getLogger("HWR").exception("EMBLXRFScan: couldn't read energy")
                return None

    def adjust_transmission(self):
        if self.cmd_adjust_transmission is not None:
            self.cmd_adjust_transmission() 
