"""
Represents Abstract XRF scan (name could be discussed) Abstract class is 
compatible with queue_entry and emits these signals during the scan:
 - xrfScanStarted  
 - xrfScanFinished
 - xrfScanFailed
 - xrfScanStatusChanged  

Functions that needs a reimplementation:
- execute_spectrum_command : actual execution command
- cancel_spectrum



"""
import os
import logging
import time
import gevent
import numpy
import abc
from HardwareRepository.TaskUtils import cleanup	
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


class AbstractXRFScan(object):
    """
    Descript. 
    """
    __metaclass__ = abc.ABCMeta
    
    def __init__(self):
        """
        Descript. :
        """
        self.can_scan = None
        self.ready_event = None
        self.scanning = None
        self.spectrum_info = None

        self.energy_motor_hwobj = None
        self.transmission_hwobj = None
        self.db_connection_hwobj = None
        self.beam_info_hwobj = None

        self.can_scan = True
        self.ready_event = gevent.event.Event()
 
    def isConnected(self):
        """
        Descript. :
        """
        return self.can_scan

    def can_spectrum(self):
        """
        Descript. :
        """
        return self.can_scan

    def start_xrf_scan(self, ct, directory, prefix, 
                       session_id = None, blsample_id = None):
        """
        Descript. :
        """
        if not self.can_scan:
            self.spectrum_command_aborted()
            return False 
   
        self.spectrum_info = {"sessionId": session_id, 
                              "blSampleId": blsample_id}
        if not os.path.isdir(directory):
            logging.getLogger().debug("XRFSpectrum: creating directory %s" % \
                                      directory)
            try:
                os.makedirs(directory)
            except OSError, diag:
                logging.getLogger().error("XRFSpectrum: error creating directory %s (%s)" \
                                          % (directory, str(diag)))
                self.emit('xrfScanStatusChanged', ("Error creating directory", ))
                self.spectrum_command_aborted()
                return False
        if not os.path.exists(directory):
            try:
                logging.getLogger().debug("XRFSpectrum: creating %s", directory)
                os.makedirs(directory)
            except:
                logging.getLogger().error("XRFSpectrum: error creating archive directory")

        filename_pattern = os.path.join(directory, "%s_%s_%%02d" % \
                                        (prefix, time.strftime("%d_%b_%Y")))
        aname_pattern = os.path.join("%s/%s_%s_%%02d" % \
                                     (directory, prefix, time.strftime("%d_%b_%Y")))

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

        self.spectrum_info["filename"] = filename
        self.spectrum_info["scanFileFullPath"] = filename
        self.spectrum_info["jpegScanFileFullPath"] = aname
        self.spectrum_info["exposureTime"] = ct
        self.spectrum_info["annotatedPymcaXfeSpectrum"] = htmlname
        self.spectrum_info["htmldir"] = directory
        self.spectrum_command_started()
        logging.getLogger().debug("XRFSpectrum: archive file is %s", aname)
        self.execute_spectrum_command(ct, filename)
        return True

    @abc.abstractmethod
    def execute_spectrum_command(self, count_time, filename):    
        """
        Descript. :
        """
        pass
   
    @abc.abstractmethod 
    def cancel_spectrum(self, *args):
        """
        Descript. :
        """
        pass

    def spectrum_command_ready(self):
        """
        Descript. :
        """
        if not self.scanning:
            self.emit('xrfSpectrumReady', (True, ))

    def spectrum_command_not_ready(self):
        """
        Descript. :
        """
        if not self.scanning:
            self.emit('xrfSpectrumReady', (False, ))

    def spectrum_command_started(self, *args):
        """
        Descript. :
        """
        self.spectrum_info['startTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit('xrfScanStarted', ())

    def spectrum_command_failed(self, *args):
        """
        Descript. :
        """
        self.spectrum_info['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.store_xrf_spectrum()
        self.emit('xrfScanFailed', ())
        self.ready_event.set()
    
    def spectrum_command_aborted(self, *args):
        """
        Descript. :
        """
        self.scanning = False
        self.emit('xrfScanFailed', ())
        self.ready_event.set()

    def spectrum_command_finished(self):
        """
        Descript. :
        """
        with cleanup(self.ready_event.set):
            self.spectrum_info['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
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
            if self.transmission_hwobj is not None: 
                self.spectrum_info["beamTransmission"] = self.transmission_hwobj.getAttFactor()
            else:
                self.spectrum_info["beamTransmission"] = None
            self.spectrum_info["energy"] = self.get_current_energy()
            if self.beam_info_hwobj is not None:
                beam_size = self.beam_info_hwobj.get_beam_size()
            else:
                beam_size = (None, None)
            self.spectrum_info["beamSizeHorizontal"] = beam_size[0]
            self.spectrum_info["beamSizeVertical"] = beam_size[1]
            mcaConfig["legend"] = "test legend"
            mcaConfig["min"] = values[0]
            mcaConfig["max"] = values[-1]
            mcaConfig["htmldir"] = self.spectrum_info["htmldir"]
            self.spectrum_info.pop("htmldir")

            fig = Figure(figsize=(15, 11))
            ax = fig.add_subplot(111)
            ax.set_title(self.spectrum_info["jpegScanFileFullPath"])
            ax.grid(True)
            ax.plot(*(zip(*calibrated_array)), **{"color" : 'black'})
            ax.set_xlabel("Energy")
            ax.set_ylabel("Counts")
            canvas = FigureCanvasAgg(fig)
            logging.getLogger().info("Rendering spectrum to PNG file : %s", 
                                     self.spectrum_info["jpegScanFileFullPath"])
            canvas.print_figure(self.spectrum_info["jpegScanFileFullPath"], dpi = 80)
            #logging.getLogger().debug("Copying .fit file to: %s", a_dir)
            #tmpname=filename.split(".")
            logging.getLogger().debug("finished %r", self.spectrum_info)
            self.store_xrf_spectrum()
            self.emit('xrfScanFinished', (mcaData, mcaCalib, mcaConfig))
            
    def spectrum_status_changed(self, status):
        """
        Descript. :
        """
        self.emit('xrfScanStatusChanged', (status, ))

    def store_xrf_spectrum(self):
        """
        Descript. :
        """
        #logging.getLogger().debug("db connection %r", self.db_connection_HO)
        logging.getLogger().debug("spectrum info %r", self.spectrum_info)
        if self.db_connection_hwobj:
            try:
                session_id = int(self.spectrum_info['sessionId'])
            except:
                return
            blsampleid = self.spectrum_info['blSampleId']
            #self.spectrum_info.pop('blSampleId')
            db_status = self.db_connection_hwobj.storeXfeSpectrum(self.spectrum_info)

    def get_current_energy(self):
        """
        Descript. :
        """
        if self.energy_motor_hwobj is not None:
            try:
                return self.energy_motor_hwobj.getPosition()
            except:
                logging.getLogger("HWR").exception("EMBLXRFScan: couldn't read energy")
