"""
Descript. :
"""
import os
import logging
import time
import gevent
import numpy
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import cleanup	
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

class EMBLXRFSpectrum(Equipment):
    """
    Descript. 
    """
    def __init__(self, name):
        """
        Descript. :
        """
        Equipment.__init__(self, name)
        self.can_scan = None
        self.ready_event = None
        self.scanning = None
        self.spectrumInfo = None

        self.energy_motor_hwobj = None
        self.transmission_hwobj = None
        self.db_connection_hwobj = None
        self.beam_info_hwobj = None

        self.chan_scan_start = None
        self.chan_scan_status = None
        self.chan_scan_consts = None

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()
 
        self.energy_motor_hwobj = self.getObjectByRole("energy")

        self.transmission_hwobj = self.getObjectByRole("transmission")
        if self.transmission_hwobj is None:
            logging.getLogger("HWR").warning("EMBLXRFSpectrum: Transmission hwobj not defined")

        self.db_connection_hwobj = self.getObjectByRole("dbserver")
        if self.db_connection_hwobj is None:
            logging.getLogger().warning("EMBLXRFSpectrum: DB hwobj not defined")

        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        if self.beam_info_hwobj is None:
            logging.getLogger("HWR").warning("EMBLXRFSpectrum: Beam info hwobj not defined")

        try:
            self.chan_scan_start = self.getChannelObject('xrfScanStart')
            self.chan_scan_status = self.getChannelObject('xrfScanStatus')
            self.chan_scan_status.connectSignal('update', self.scan_status_update)
            self.chan_scan_consts = self.getChannelObject('xrfScanConsts')
            self.can_scan = True
        except:
            logging.getLogger("HWR").error('EMBLXRFSpectrum: unable to connect to scan channel(s).')

        if self.isConnected():
            self.sConnected()

    def scan_status_update(self, status):
        """
        Descript. :
        """
        if self.scanning == True:
            if status == 'scanning':
                logging.getLogger("HWR").info('XRF scan in progress...')
            elif status == 'ready':
                if self.scanning is True:
                    self.spectrumCommandFinished()
                    logging.getLogger("HWR").info('XRF scan finished')
            elif status == 'aborting':
                if self.scanning is True:
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
f      """
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

    def startXrfSpectrum(self, ct, directory, prefix, session_id = None, blsample_id = None):
        """
        Descript. :
        """
        if not self.can_scan:
            self.spectrumCommandAborted()
            return False 
  
        self.spectrumInfo = {"sessionId": session_id, "blSampleId": blsample_id}
        if not os.path.isdir(directory):
            logging.getLogger().debug("EMBLXRFSpectrum: creating directory %s" % directory)
            try:
                os.makedirs(directory)
            except OSError, diag:
                logging.getLogger().error("EMBLXRFSpectrum: error creating directory %s (%s)" % (directory, str(diag)))
                self.emit('xrfScanStatusChanged', ("Error creating directory", ))
                self.spectrumCommandAborted()
                return False
        if not os.path.exists(directory):
            try:
                logging.getLogger().debug("EMBLXRFSpectrum: creating %s", directory)
                os.makedirs(directory)
            except:
                logging.getLogger().error("EMBLXRFSpectrum: error creating archive directory")

        filename_pattern = os.path.join(directory, "%s_%s_%%02d" % (prefix, time.strftime("%d_%b_%Y")))
        aname_pattern = os.path.join("%s/%s_%s_%%02d" % (directory, prefix, time.strftime("%d_%b_%Y")))

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
        self.spectrumInfo["scanFileFullPath"] = filename
        self.spectrumInfo["jpegScanFileFullPath"] = aname
        self.spectrumInfo["exposureTime"] = ct
        self.spectrumInfo["annotatedPymcaXfeSpectrum"] = htmlname
        self.spectrumInfo["htmldir"] = directory
        self.spectrumCommandStarted()
        logging.getLogger().debug("EMBLXRFSpectrum: archive file is %s", aname)
        self.reallyStartXrfSpectrum(ct, filename)
        return True
        
    def reallyStartXrfSpectrum(self, ct, filename):    
        """
        Descript. :
        """
        try:
            self.chan_scan_start.setValue(ct)
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
        self.spectrumInfo['startTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit('xrfScanStarted', ())

    def spectrumCommandFailed(self, *args):
        """
        Descript. :
        """
        self.spectrumInfo['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
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
            self.spectrumInfo['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.scanning = False
            values = list(self.chan_scan_start.getValue())
            mcaCalib = self.chan_scan_consts.getValue()
            mcaData = []
            calibrated_data = []
            for n, value in enumerate(values):
                mcaData.append((n, value))
                energy = mcaCalib[0] + mcaCalib[1] * n + mcaCalib[2] * n * n
                calibrated_line = [energy, value]
                calibrated_data.append(calibrated_line)
            calibrated_array = numpy.array(calibrated_data)
            mcaConfig = {}

            self.spectrumInfo["beamTransmission"] = self.transmission_hwobj.getAttFactor()
            self.spectrumInfo["energy"] = self.getCurrentEnergy()
            beam_size = self.beam_info_hwobj.get_beam_size()
            self.spectrumInfo["beamSizeHorizontal"] = beam_size[0]
            self.spectrumInfo["beamSizeVertical"] = beam_size[1]
            mcaConfig["legend"] = "test legend"
            mcaConfig["min"] = values[0]
            mcaConfig["max"] = values[-1]
            mcaConfig["htmldir"] = self.spectrumInfo["htmldir"]
            self.spectrumInfo.pop("htmldir")

            fig = Figure(figsize=(15, 11))
            ax = fig.add_subplot(111)
            ax.set_title(self.spectrumInfo["jpegScanFileFullPath"])
            ax.grid(True)
            ax.plot(*(zip(*calibrated_array)), **{"color" : 'black'})
            ax.set_xlabel("Energy")
            ax.set_ylabel("Counts")
            canvas = FigureCanvasAgg(fig)
            logging.getLogger().info("Rendering spectrum to PNG file : %s", self.spectrumInfo["jpegScanFileFullPath"])
            canvas.print_figure(self.spectrumInfo["jpegScanFileFullPath"], dpi = 80)
            #logging.getLogger().debug("Copying .fit file to: %s", a_dir)
            #tmpname=filename.split(".")
            logging.getLogger().debug("finished %r", self.spectrumInfo)
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
        logging.getLogger().debug("spectrum info %r", self.spectrumInfo)
        if self.db_connection_hwobj:
            try:
                session_id = int(self.spectrumInfo['sessionId'])
            except:
                return
            blsampleid = self.spectrumInfo['blSampleId']
            #self.spectrumInfo.pop('blSampleId')
            db_status = self.db_connection_hwobj.storeXfeSpectrum(self.spectrumInfo)

    def getCurrentEnergy(self):
        """
        Descript. :
        """
        if self.energy_motor_hwobj is not None:
            try:
                return self.energy_motor_hwobj.getPosition()
            except:
                logging.getLogger("HWR").exception("EMBLXRFScan: couldn't read energy")
                return None
