# -*- coding: utf-8 -*-
import sys
import os
import time
from PIL import Image
import numpy
from PyQt4.QtCore import QThread, QMutex
sys.path.append("/opt/dectris/albula/4.0/python/")
try:
    from dectris import albula
except:
    print("albula module not found")
try:
    from hidra import Transfer
except:
    print("hidra module not found")

class LiveView(QThread):
    FILETYPE_CBF = 0
    FILETYPE_TIF = 1
    FILETYPE_HDF5 = 2

    alive = False
    path = ""
    filetype = 0
    interval = 0.5 #s
    stoptimer = -1.0
    stream = False

    viewer = None
    subframe = None
    mutex = None

    zmqSignalIp = "haspp11eval01.desy.de"
    zmqDataPort = "50021"
    basePath = "/gpfs"

    def __init__(self, path=None, filetype=None, interval=None, parent=None):
        QThread.__init__(self, parent)
        if path is not None:
            self.path = path
        if filetype is not None:
            self.filetype = filetype
        if interval is not None:
            self.interval = interval
        self.eigerMonitor = None
        self.eigerThread = None
        if parent is not None and hasattr(parent, "eigerThread"):
            try:
                property = parent.eigerThread.proxyMonitor.get_property("Host")["Host"]
            except:
                pass
            else:
                self.eigerMonitor = albula.DEigerMonitor(property[0])
                self.eigerThread = parent.eigerThread
        self.eigerMask16M = None
        self.eigerMask4M = None
        mask_path_16m = os.path.dirname(sys.argv[0]) + "/img/pixel_mask.tif"
        mask_path_4m = os.path.dirname(sys.argv[0]) + "/img/pixel_mask_4m.tif"
        try:
            mask_tif_16m = Image.open(mask_path_16m)
            mask_tif_4m = Image.open(mask_path_4m)
        except:
            pass
        else:
            mask_array_16m = numpy.asarray(mask_tif_16m)
            self.eigerMask16M = albula.DImage(mask_array_16m)
            mask_array_4m = numpy.asarray(mask_tif_4m)
            self.eigerMask4M = albula.DImage(mask_array_4m)
        self.mutex = QMutex()
        self.zmqQuery = None


    def start(self, path=None, filetype=None, interval=None, stream=False):
        if path is not None:
            self.path = path
        if filetype is not None:
            self.filetype = filetype
        if interval is not None:
            self.interval = interval
        self.stream = stream
        self.stoptimer = -1
        if self.filetype in [LiveView.FILETYPE_CBF, LiveView.FILETYPE_TIF]:
            if stream:
                connectionType = "STREAM_METADATA"
            else:
                connectionType = "QUERY_NEXT_METADATA"
            if self.zmqQuery is not None:
                self.zmqQuery.stop()
            self.zmqQuery = Transfer(connectionType, self.zmqSignalIp)
            self.zmqQuery.initiate([os.uname()[1], self.zmqDataPort, "1", [".cbf", ".tif"]])
            self.zmqQuery.start(self.zmqDataPort)
        elif self.filetype == LiveView.FILETYPE_HDF5 and self.eigerThread is not None:
            self.eigerThread.setMonitorMode("enabled")
            if stream:
                self.eigerThread.setMonitorDiscardNew(False)
            else:
                self.eigerThread.clearMonitorBuffer()
                self.eigerThread.setMonitorDiscardNew(True)
            
        QThread.start(self)

    def stop(self, interval=0.0):
        if self.stoptimer < 0.0 and interval > 0.0:
            print("Live view thread: Stopping in %d seconds"%interval)
            self.stoptimer = interval
            return
        print("Live view thread: Stopping thread")
        self.alive = False
        self.wait() # waits until run stops on his own


    def run(self):
        self.alive = True
        print("Live view thread: started")
        suffix = [".cbf", ".tif", ".hdf5"]
        if self.subframe is None:
            try:
                self.subframe = self.viewer.openSubFrame()
            except:
                self.viewer = albula.openMainFrame()
                self.subframe = self.viewer.openSubFrame()
        if self.filetype in [LiveView.FILETYPE_CBF, LiveView.FILETYPE_TIF]:
            # open viewer
            while self.alive:
                # find latest image
                self.mutex.lock()

                # get latest file from reveiver
                timestamp = time.time()
                [metadata, data] = self.zmqQuery.get(self.interval * 1000)
                received_file = self.zmqQuery.generate_target_filepath(self.basePath, metadata)

                if received_file is not None and self.alive:
                    # load image
                    try:
                        img = albula.readImage(received_file, 500)
                    # file not readable
                    except:
                        self.mutex.unlock()
                        continue
                    # display image
                    try:
                        self.subframe.loadImage(img)
                    # viewer or subframe has been closed by the user
                    except:
                        self.mutex.unlock()
                        time.sleep(0.1)
                        try:
                            self.subframe = self.viewer.openSubFrame()
                        except:
                            self.viewer = albula.openMainFrame()
                            self.subframe = self.viewer.openSubFrame()
                        continue
                self.mutex.unlock()

                # wait interval
                interval = time.time() - timestamp
                if self.stoptimer > 0:
                    self.stoptimer -= interval
                    if self.stoptimer <= 0.0:
                        self.stoptimer = -1.0
                        self.alive = False
                while interval < self.interval and self.alive:
                    if self.stoptimer > 0.0:
                        self.stoptimer -= 0.05
                        if self.stoptimer <= 0.0:
                            self.stoptimer = -1.0
                            self.alive = False
                    time.sleep(0.05)
                    interval += 0.05
        elif self.filetype == LiveView.FILETYPE_HDF5 and self.eigerThread is not None:
            wavelength = 12398.4/(self.eigerThread.photonEnergy)
            try:
                detector_distance = self.eigerThread.proxyEiger.read_attribute("DetectorDistance").value
                beam_center_x = self.eigerThread.proxyEiger.read_attribute("BeamCenterX").value
                beam_center_y = self.eigerThread.proxyEiger.read_attribute("BeamCenterY").value
            except:
                detector_distance = 1.0
                beam_center_x = 2074
                beam_center_y = 2181
            # open viewer
            while self.alive:
                # get latest file from reveiver
                timestamp = time.time()
                if self.stream:
                    try:
                        img = self.eigerMonitor.next()
                    except:
                        time.sleep(0.1)
                        if self.stoptimer > 0:
                            self.stoptimer -= 0.1
                            if self.stoptimer <= 0.0:
                                self.stoptimer = -1.0
                                self.alive = False
                        continue
                else:
                    try:
                        img = self.eigerMonitor.monitor()
                        self.eigerThread.clearMonitorBuffer()
                    except:
                        print(sys.exc_info())
                        continue
                # display image
                img.optionalData().set_wavelength(wavelength)
                img.optionalData().set_detector_distance(detector_distance)
                img.optionalData().set_beam_center_x(beam_center_x)
                img.optionalData().set_beam_center_y(beam_center_y)
                img.optionalData().set_x_pixel_size(0.000075)
                img.optionalData().set_y_pixel_size(0.000075)
                if self.eigerMask16M is not None and img.width() == 4148:
                    img.optionalData().set_pixel_mask(self.eigerMask16M)
                elif self.eigerMask4M is not None and img.width() == 2068:
                    img.optionalData().set_pixel_mask(self.eigerMask4M)
                try:
                    self.subframe.hideResolutionRings()
                    self.subframe.loadImage(img)
                    self.subframe.showResolutionRings()
                # viewer or subframe has been closed by the user
                except:
                    time.sleep(0.1)
                    try:
                        self.subframe = self.viewer.openSubFrame()
                    except:
                        self.viewer = albula.openMainFrame()
                        self.subframe = self.viewer.openSubFrame()
                    try:
                        self.subframe.hideResolutionRings()
                        self.subframe.loadImage(img)
                        self.subframe.showResolutionRings()
                    except:
                        pass
                    continue
                # wait interval
                interval = time.time() - timestamp
                if self.stoptimer > 0:
                    self.stoptimer -= interval
                    if self.stoptimer <= 0.0:
                        self.stoptimer = -1.0
                        self.alive = False
                if self.stream:
                    time.sleep(0.1)
                    continue
                while interval < self.interval and self.alive:
                    if self.stoptimer > 0.0:
                        self.stoptimer -= 0.05
                        if self.stoptimer <= 0.0:
                            self.stoptimer = -1.0
                            self.alive = False
                    time.sleep(0.05)
                    interval += 0.05

        print("Live view thread: Thread for Live view died")
        self.alive = False
        if self.filetype in [LiveView.FILETYPE_CBF, LiveView.FILETYPE_TIF]:
            self.zmqQuery.stop()
            self.zmqQuery = None

    def setPath(self, path=None):
        self.mutex.lock()
        if path is not None:
            self.path = path
        self.mutex.unlock()

    def setFiletype(self, filetype=None):
        restart = False
        if self.alive:
            restart = True
            self.stop()
        if filetype is not None:
            self.filetype = filetype
        if restart:
            self.start()

    def setInterval(self, interval=None):
        if interval is not None:
            self.interval = interval

if __name__ == '__main__':

    lv = LiveView()

    lv.start()

    time.sleep(200)
    lv.stop()


