# -*- coding: utf-8 -*-
#$Log: XfeSpectrum.py,v $
#Revision 1.1  2007/06/06 14:31:11  beteva
#Initial revision
#
from qt import *
from HardwareRepository.BaseHardwareObjects import Equipment
import logging
import os
import time
import types
from XfeCollect import XfeCollect

class XfeSpectrumPX2(Equipment):
    def init(self):
        self.scanning = None
        self.moving = None
        #self.doSpectrum = None
        
        self.storeSpectrumThread = None
        if self.isConnected():
            self.sConnected()
        #if True:
            #try:
                #self.energySpectrumArgs=self.getChannelObject('spectrum_args')
            #except KeyError:
                #logging.getLogger().warning('XRFSpectrum: error initializing energy spectrum arguments (missing channel)')
                #self.energySpectrumArgs=None
            #try:
                #self.spectrumStatusMessage=self.getChannelObject('spectrumStatusMsg')
            #except KeyError:
                #self.spectrumStatusMessage=None
                #logging.getLogger().warning('XRFSpectrum: energy messages will not appear (missing channel)')
            #else:
                #self.connect(self.spectrumStatusMessage,'update',self.spectrumStatusChanged)

            #try:
                #self.doSpectrum.connectSignal('commandReplyArrived', self.spectrumCommandFinished)
                #self.doSpectrum.connectSignal('commandBeginWaitReply', self.spectrumCommandStarted)
                #self.doSpectrum.connectSignal('commandFailed', self.spectrumCommandFailed)
                #self.doSpectrum.connectSignal('commandAborted', self.spectrumCommandAborted)
                #self.doSpectrum.connectSignal('commandReady', self.spectrumCommandReady)
                #self.doSpectrum.connectSignal('commandNotReady', self.spectrumCommandNotReady)
            #except AttributeError, diag:
                #logging.getLogger().warning('XRFSpectrum: error initializing energy spectrum (%s)' % str(diag))
                #self.doSpectrum=None
            #else:
                #self.doSpectrum.connectSignal("connected", self.sConnected)
                #self.doSpectrum.connectSignal("disconnected", self.sDisconnected)
 
            #self.dbConnection=self.getObjectByRole("dbserver")
            #if self.dbConnection is None:
                #logging.getLogger().warning('XRFSpectrum: you should specify the database hardware object')
            #self.spectrumInfo=None

            #if self.isConnected():
               #self.sConnected()

    def doSpectrum(self): #, ct, filename):
        self.xfeCollect.measureSpectrum()
        self.spectrumCommandFinished(0)
        return self.xfeCollect.get_calibrated_energies(), self.xfeCollect.getSpectrum()
    
    def isConnected(self):
        return True
        try:
          return self.xfeCollect.isConnected()
        except:
          return False 

    # Handler for spec connection
    def sConnected(self):
        self.emit('connected', ())
        curr = self.getSpectrumParams()

    # Handler for spec disconnection
    def sDisconnected(self):
        self.emit('disconnected', ())

    # Energy spectrum commands
    def canSpectrum(self):
        if not self.isConnected():
            return False
        return self.doSpectrum is not None

    def startXfeSpectrum(self, ct, directory, prefix, session_id = None, blsample_id = None):
        logging.getLogger().debug("Xfepectrum: startXfeSpectrum")
        
        #inintializing the collect object
        self.xfeCollect = XfeCollect(ct, directory, prefix, sessionId = session_id, sampleId = blsample_id)
        
        print 'ct, directory', ct, directory
        self.spectrumInfo = {"sessionId": session_id}
        self.spectrumInfo["blSampleId"] = blsample_id
        if not os.path.isdir(directory):
            logging.getLogger().debug("XfeSpectrum: creating directory %s" % directory)
            try:
                os.makedirs(directory)
            except OSError, diag:
                logging.getLogger().error("XfeSpectrum: error creating directory %s (%s)" % (directory,str(diag)))
                self.emit('spectrumStatusChanged', ("Error creating directory",))
                return False
        curr = self.getSpectrumParams()
        print 'curr', curr
        try:
            curr["escan_dir"]=directory
            curr["escan_prefix"]=prefix
        except TypeError:
            curr={}
            curr["escan_dir"]=directory
            curr["escan_prefix"]=prefix

        #a = directory.split(os.path.sep)
        #suffix_path = os.path.join(*a[4:])
        #if 'inhouse' in a :
            #a_dir = os.path.join('/data/pyarch/', a[2], suffix_path)
        #else:
            #a_dir = os.path.join('/data/pyarch/',a[4],a[3],*a[5:])
        #if a_dir[-1]!=os.path.sep:
            #a_dir+=os.path.sep
        #if not os.path.exists(a_dir):
            #try:
                ##logging.getLogger().debug("XRFSpectrum: creating %s", a_dir)
                #os.makedirs(a_dir)
            #except:
                #try:
                    #smis_name=os.environ["SMIS_BEAMLINE_NAME"].lower()
                    #x,y=smis_name.split("-")
                    #bldir=x+"eh"+y
                #except:
                    #bldir=os.environ["SMIS_BEAMLINE_NAME"].lower()
                #tmp_dir = "/data/pyarch/%s" % bldir
                #logging.getLogger().error("XRFSpectrum: error creating archive directory - the data will be saved in %s instead", tmp_dir)
        a_dir = os.path.dirname(directory)
        filename_pattern = os.path.join(directory, "%s_%s_%%02d" % (prefix,time.strftime("%d_%b_%Y")) )
        aname_pattern = os.path.join("%s/%s_%s_%%02d" % (a_dir,prefix,time.strftime("%d_%b_%Y")))

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
            i=i+1

        self.spectrumInfo["filename"] = filename
        #self.spectrumInfo["scanFileFullPath"] = filename
        self.spectrumInfo["jpegScanFileFullPath"] = aname
        self.spectrumInfo["exposureTime"] = ct
        self.spectrumInfo["annotatedPymcaXfeSpectrum"] = htmlname
        logging.getLogger().debug("XfeSpectrum: archive file is %s", aname)
        try:
            #self.doSpectrum(ct, filename)
            self.doSpectrum()
        except:
            logging.getLogger().exception('XfeSpectrum: problem calling doSpectrum method')
            self.emit('spectrumStatusChanged', ("Error problem spec macro",))
            self.emit('xfeSpectrumFailed', ())
            return False
        return True

    def cancelXfeSpectrum(self):
        if self.scanning:
            #self.doSpectrum.abort()
            self.xfeCollect.cancelXfeSpectrum()
            
    def spectrumCommandReady(self):
        if not self.scanning:
            self.emit('xfeSpectrumReady', (True,))

    def spectrumCommandNotReady(self):
        if not self.scanning:
            self.emit('xfeSpectrumReady', (False,))

    def spectrumCommandStarted(self):
        self.spectrumInfo['startTime']=time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit('xfeSpectrumStarted', ())

    def spectrumCommandFailed(self):
        self.spectrumInfo['endTime']=time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.storeXfeSpectrum()
        self.emit('xfeSpectrumFailed', ())
    
    def spectrumCommandAborted(self):
        self.scanning = False
        self.emit('xfeSpectrumFailed', ())

    def spectrumCommandFinished(self,result):
        self.spectrumInfo['endTime']=time.strftime("%Y-%m-%d %H:%M:%S")
        logging.getLogger().debug("XRFSpectrum: XRF spectrum result is %s" % result)
        self.scanning = False

        if result==0:
            #mcaData = self.getChannelObject('mca_data').getValue()
            mcaData = self.xfeCollect.getXvals(), self.xfeCollect.getSpectrum()
            #mcaCalib = self.getChannelObject('calib_data').getValue()
            mcaCalib = self.xfeCollect.get_calibration() #None
            #mcaConfig = self.getChannelObject('config_data').getValue()
            mcaConfig = self.xfeCollect.getMcaConfig()
            self.spectrumInfo["beamTransmission"] = mcaConfig['att']
            self.spectrumInfo["energy"] = mcaConfig['energy']
            self.spectrumInfo["beamSizeHorizontal"] = float(mcaConfig['bsX'])
            self.spectrumInfo["beamSizeVertical"] = float(mcaConfig['bsY'])
            mcaConfig["legend"] = self.spectrumInfo["annotatedPymcaXfeSpectrum"]
                        
            #here move the png file
            pf = self.spectrumInfo["filename"].split(".")
            pngfile = os.path.extsep.join((pf[0], "png"))
            if os.path.isfile(pngfile) is True :
                try :
                    copy(pngfile,self.spectrumInfo["jpegScanFileFullPath"])
                except:
                    logging.getLogger().error("XRFSpectrum: cannot copy %s", pngfile)
            
            logging.getLogger().debug("finished %r", self.spectrumInfo)
            self.storeXfeSpectrum()
            self.emit('xfeSpectrumFinished', (mcaData, mcaCalib, mcaConfig))
        else:
            self.spectrumCommandFailed()
            
    def spectrumStatusChanged(self,status):
        self.emit('spectrumStatusChanged', (status,))

    def storeXfeSpectrum(self):
        self.xfeCollect.saveData()
        #logging.getLogger().debug("db connection %r", self.dbConnection)
        #logging.getLogger().debug("spectrum info %r", self.spectrumInfo)
        #if self.dbConnection is None:
            #return
        #try:
            #session_id=int(self.spectrumInfo['sessionId'])
        #except:
            #return
        #self.storeSpectrumThread=StoreXfeSpectrumThread(self.dbConnection,self.spectrumInfo)
        #self.storeSpectrumThread.start()
        

    def updateXfeSpectrum(self, spectrum_id, jpeg_spectrum_filename):
        pass

    def getSpectrumParams(self):
        try:
            self.curr='parameters' #self.energySpectrumArgs.getValue()
            return self.curr
        except NameError, diag:
            logging.getLogger().exception('XRFSpectrum: error getting xrfspectrum parameters (%s)' % str(diag))
            self.emit('spectrumStatusChanged', ("Error getting xrfspectrum parameters",))
            return False


    def setSpectrumParams(self,pars):
        self.energySpectrumArgs.setValue(pars)

class StoreXfeSpectrumThread(QThread):
    def __init__(self,db_conn,spectrum_info):
        QThread.__init__(self)
        self.dbConnection=db_conn
        self.spectrumInfo=dict(spectrum_info)

    def run(self):
        blsampleid=self.spectrumInfo['blSampleId']
        self.spectrumInfo.pop('blSampleId')
        db_status=self.dbConnection.storeXfeSpectrum(self.spectrumInfo)
        if blsampleid is not None:
            try:
                xfespectrumid=int(db_status['xfeFluorescenceSpectrumId'])
            except:
                pass
