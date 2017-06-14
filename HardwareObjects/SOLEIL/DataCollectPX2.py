# -*- coding: utf-8 -*-
"""
BlissFramework's hardware object to perform the data collection on protein-crystallography
beamlines. It controls all involved systems: spec, sample changer, database, etc., so it
loads several hardware objects.

Some documentation on the following methods is written on the method header itself.


Main APIs
---------
collect(owner<string?>,arguments<dict>,callback<method>=None)
<dict> sanityCheck(arguments<dict>)
stopCollect(owner<string?>)
abortCollect(owner<string?>)


State APIs
----------
<bool> isConnected()
<bool> isReady()
<float> getAxisPosition()
<dict> getBeamlineConfiguration(keys<None/list>)
<dict> getBeamlineCurrentParameters(keys<None/list>)
<int> getLastImageTakenBySpec()
<SampleChanger> sampleChangerHO()
<MiniDiff> miniDiffHO()
<ISPyBClient> dbServerHO()
<string> directoryPrefix()
<bool> isInhouseUser(proposal_code<string>,proposal_number<int>)


Auxiliary GUI APIs
------------------
setBrick(brick<QWidget>)
setCentringStatus(centring_status<dict>)
collectEvent(method<method>,arguments<tuple>):


Callback methods to be explicitly called from outside to continue the data collection
-------------------------------------------------------------------------------------
sampleAcceptCentring(accepted<bool>,centring_status<dict>)


Internal slots (to continue the data collection)
------------------------------------------------
minidiffCentringAccepted(accepted<bool>,centring_status<dict>)
sampleLoaded(already_loaded<bool>=False)
loadSampleFailed(state<string>)
sampleUnloaded()
unloadSampleFailed(state<string>)


Module APIs
-----------
<bool> isConsoleApplication()
startActionsThread(actions_obj<instance>)
<tuple> getArchiveDirectory(directory_prefix<string>,directory<string>=None,filename<string>=None)
<int; qt.QEvent.User> COLLECT_GUI_EVENT
<class; qt.QCustomEvent> CollectGUIEvent


Signals
-------
collectDisconnected()
[emitted when spec is disconnected]

collectConnected()
[emitted when spec is connected]

collectReady(state<bool>)
[emits the readiness of the h.o. to collect data: emitted when spec is busy (state=False),
ready(state=True) and also when collecting (state=False at start, state=True at end)]

collectAxisMotorMoved(pos<float>)
[emitted when the axis/phi motor moves]

collectStarted(owner<string?>)
[signals the start of a data collection; the owner is the data collection owner given to
the collect API; emitted right after the signal collectReady(False)]

collectOscillationStarted(owner<string?>,blsampleid<None/int>,sample_code<None/string>,sample_location<None/tuple>,arguments<dict>)
[emitted right after the collectStarted(owner) signal; gives more information about the
oscillation: the blsampleid of the sample in the ISPyB database, its sample changer barcode
and location, and the already given collectionarguments to the collect API]

collectMountingSample(sample_code<string>,sample_location<tuple>,mounted<bool/None>)
[emitted when the data collect object is requesting the sample changer to mount a sample; the
first arguments are the sample bar/matrix code and the sample location tuple (basket,vial);
the mount parameter is: None when the data collect h.o. is waiting for the mounting, False if
there was a problem with the mounting, True if the mounting was successful thus the data collect
h.o. is continuing with the collection]

collectValidateCentring(sample_was_loaded<bool=True>,fileinfo<dict>)
[emitted when the sample changer loaded a sample at the initialization of a data collection
and wants the user to centre it; the sample_was_loaded arguments should always be True; the
fileinfo is the dictionary of the "fileinfo" key of the current collection parameters]

collectRejectCentring()
[emitted when the data collection is waiting for the sample centring but either user wants
to stop the data collection or the centring timeout occured]

collectNumberOfFrames(state<bool>,num_images<int/None>)
[emitted when calling the oscillation spec macro; if there was a problem in the call (not in
the execution!) then state is False and the collection will fail; otherwise state is True and
num_images in the total number of images of the collection]

collectImageTaken(image_number<int>)
[emitted when an image is exposed; image_number is the index always starting with 1]

collectUnmountingSample(unmounted<bool/None>)
[emitted when the data collect object, after mounting a sample at initialization time, tries
to unmount the same sample after the oscillation macro finishes; unthe mount parameter is: None
when the data collect h.o. is waiting for the unmounting, False if there was a problem with the
unmounting, True if the unmounting was successful thus the data collect h.o. is finishing the
collection]

collectOscillationFailed(owner<string?>,stat<None/bool=False>,msg<string>,col_id<int>)
[always emitted if the collection fails for whatever reason (spec/centring/mounting); parameters
are the collection owner, the status (same as collectFailed), a finished message and the data
collection id entry in the database]

collectFailed(owner<string?>,stat<bool>,msg<string>)
[emitted after the collectOscillationFailed and before the collectReady signals; parameters
are the owner of the just failed collection, the status (None if the data collection was
stopped at user's request, or some other non-fatal or unknown error; False if aborted) and
a stopped/error message (same as the collectOscillationFailed message)]

collectOscillationFinished(owner<string?>,stat<bool=True>,msg<string>,col_id<int>)
[emitted after the oscillation spec macro finishes, the database getting updated, and eventually
unmountint of the sample; parameters are the collection owner, the status (should always be
True), a finished message and the data collection id entry in the database]

collectEnded(owner<string?>,stat<bool>,msg<string>)
[emitted after the collectOscillationFinished and before the collectReady signals; parameters
are the owner of the just finished collection, the status (should always be True) and a finished
message (same as the collectOscillationFinished message)]


(See the end of this file for an example of the XML configuration file.)
"""



### Modules ###
from HardwareRepository.BaseHardwareObjects import Procedure
from HardwareRepository import HardwareRepository
import logging
import qt
import Queue
import time
import os
import commands
import types
import string
import subprocess
import math
import threading
import copy
import signal
import xmlrpclib

## Added MS 
import socket # for adxv visualisation
import pprint  # this was missing for some strange reason
from HardwareRepository.Command.Tango import DeviceProxy
import shlex 
import Collect
##

### Useful stuff from Proxima 1 
def make_dir(dirname):    
    try:
        os.mkdir(dirname)
        os.chmod(dirname, 0777)
    except OSError:
        pass
    except Exception, err:
        print "Error in creating process directory %s:" % dirname, err

def make_process_dir(dirname):
    _pdir = os.path.join(dirname, "process")
    make_dir(_pdir)

def write_goimg(path):
    dirname = "/927bis/ccd/log/.goimg"
    db = "goimg.db"
    db_f = os.path.join(dirname,db)
    if db in os.listdir(dirname):
        os.remove(db_f)
    dbo = open(db_f, "w")
    dbo.write(path)
    dbo.close()
    os.chmod(db_f, 0777)
###

"""
CollectGUIEvent
    Description: Class to store a method and arguments. Objects should be posted to a QWidget
                 Used to execute methods that might change the GUI from outside the main
                 GUI thread.
    Type       : class (qt.QCustomEvent)
    Arguments  : method    (function)
                 arguments (tuple/list; parameters for the method)
"""
COLLECT_GUI_EVENT = qt.QEvent.User
class CollectGUIEvent(qt.QCustomEvent):
    def __init__(self,method,arguments):
        qt.QCustomEvent.__init__(self,COLLECT_GUI_EVENT)
        self.method=method
        self.arguments=arguments

"""
postCollectGUIEvent
    Description : Posts a custom event to a brick/QWidget.
    Type        : method
    Arguments   : brick     (instance; expects a BlisWidget/qt.QWidget object)
                  method    (function)
                  arguments (tuple/list; parameters for the method)
    Returns     : nothing
    Side-effects: Creates an object of type CollectGUIEvent and posts it to the brick.
                  Returns immediately!
    Comments    : The method is not executed immediately: it's stored in a queue to
                  be processed later.
"""
def postCollectGUIEvent(brick,method,arguments):
    if brick is not None:
        qt.QApplication.postEvent(brick,CollectGUIEvent(method,arguments))
    else:
        #logging.getLogger("HWR").debug("DataCollect: have a GUI event but nobody's listening!")
        pass



"""
imageQueue
    Description: Used to stores collected images (filename) along its parameters (intensity,
                 from spec, last machine current and message, etc.) to be stored in ISPyB
    Type       : Global variable, instance of Queue.Queue
    Producer   : The DataCollect h.o. instance, when getting an update on the image spec channel
    Consumer   : A dedicated thread that reads the images and stores them is ISPyB
    Notes      : The convertion of detector images to jpegs was also initiated here, but now
                 it's deprecated since the detector software writes the jpegs itself.
"""
imageQueue=Queue.Queue()



"""
isConsoleApplication
    Description: Checks if the current application is graphical or just console
    Type       : method
    Arguments  : none
    Returns    : bool; False if there's a Qt application created with type different of
                 Tty, otherwise True
    Notes      : If called inside a graphical application before the QApplication object
                 is created, it will return True (which is incorrect...)
"""
def isConsoleApplication():
    try:
        return qt.qApp.type()==qt.QApplication.Tty
    except:
        return True



"""
DataCollect
    Type: class
    (please see file and method headers for details)
"""
class DataCollectPX2(Procedure):
    """
    Some class configuration parameters
    """
    print "Debug MS 13.09.2012, DataCollectPX2 hobj"
    SPEC_PARAMS_TIMEOUT  = 15     # Timeout (sec) while waiting for spec validate parameters macro
    LOADSAMPLE_TIMEOUT   = 4*60   # Timeout (sec) waiting for the sample changer to load a sample
    UNLOADSAMPLE_TIMEOUT = 4*60   # Timeout (sec) waiting for the sample changer to unload a sample
    CENTRESAMPLE_TIMEOUT = 15*60  # Timeout (sec) waiting for centring the crystal
    CANCELCENTRE_TIMEOUT = 30     # Timeout (sec) waiting for cancelling the centring

    LOADSAMPLE_TRIES      = 3 # Number of tries to load a sample
    UNLOADSAMPLE_TRIES    = 3 # Number of tries to unload a sample
    MAKEDIRS_TRIES        = 3 # Number of tries to create a directory
    SPEC_PARAMETERS_TRIES = 3 # Number of tries to get the beamline parameters from spec

    CENTRING_CANCELLED_SLEEP = -1  # Number of seconds to sleep after cancelling the centring or -1
                                   # to wait until timeout CANCELCENTRE_TIMEOUT
    MAKEDIRS_TRY_SLEEP       = 1.0 # Number of seconds to sleep before retrying to create a directory

    """
    Dictionaries describing what should/could be present in the h.o. XML configuration file.
    The jpegserver and abortcleanupcmd are deprecated, although the code that uses them still
    exists.
    """
    MANDATORY_CHANNELS={} #{"arguments":"arguments"} #{"arguments":"arguments",\
        #"imageCollected":"image information"}
    OPTIONAL_CHANNELS={} #{"stopscan":"stop data collection",\
        #"messages":"messages",\
        #"fatalCollect":"fatal data collection return channel",
        #"xdsFile":"xdsFile"}
    MANDATORY_HO={"mxlocal":"beamline xml configuration file"}
    OPTIONAL_HO={"samplechanger":"sample changer",\
        "minidiff":"minidiff",\
        "slitbox":"slitbox",\
        "dbserver":"DB Server",\
        "safetyshutter":"safety shutter",\
        "machcurrent":"machine current",\
        "cryostream":"cryo stream",\
        "energyscan":"energy scan",\
        "BLEnergy":"beamline energy",\
        "detdistmotor":"detector distance motor",\
        "resmotor":"resolution motor",\
        "transmission":"transmission/beam attenuation",\
        "jpegserver":"jpeg server"}
    MANDATORY_CMDS={} #{"macroCollect":"data collect macro"} #MS 11.09.2012
    OPTIONAL_CMDS={"macroValidateParameters":"validation of the data collection parameters macro"}
    MANDATORY_PROPS={"directoryprefix":"standard directory prefix"}
    OPTIONAL_PROPS={"abortcleanupcmd":"abort cleanup command", \
                    "customDirectoryPrefix":"used instead of standard directory Prefix",\
                    "autoProcessingServer":"name of processing server"}

    """
    init
        Description : Called by the super class to initialize the h.o.
        Type        : method
        Arguments   : none
        Returns     : nothing
        Signals     : collectConnected, collectDisconnected, collectReady
    """
    def init(self):
        # Create instance variables
        self.configOk=True
        self.xds_dir=None
        print "DataCollect init()"
        self.persistentValues = {
                                    "owner":None,
                                    "callback":None,
                                    "stopped":None,
                                    "aborted":None,
                                    "abortRequested":None,
                                    "macroStarted":None,
                                    "logFile":None,
                                    "arguments":{},
                                    "adxv": None
                                }
        # Variable to get the datacollection ID into edna. It could be the persistent values arguments but these are always none when I tried to read them
        self.currentDataCollectionId = None
            
        try:
            self.adscDevice = DeviceProxy(self.getProperty('adsc'))
        except:
            logging.getLogger("HWR").error("%s: unknown device name", self.getProperty('adsc'))
            
        try:
            self.limaadscDevice = DeviceProxy(self.getProperty('limaadsc'))
        except:
            logging.getLogger("HWR").error("%s: unknown device name", self.getProperty('limaadsc'))
        
        try:
            self.md2device = DeviceProxy(self.getProperty('md2'))
        except:
            logging.getLogger("HWR").error("%s: unknown device name", self.getProperty('md2'))
            
        if isConsoleApplication():
            self.globalLock=PyLock()
            self.validLock=PyLock()
            self.validCond=PyCondition()
        else:
            self.globalLock=QtLock()
            self.validLock=QtLock()
            self.validCond=QtCondition()

        self.lastReady=None
        self.lastConnected=None

        self.collectionHistory=0
        self.Brick=None
        self.threadRefs={}
        self.postImageThread=None

        self.lastMachineCurrent=None
        self.lastMachineMessage=None
        self.lastMachineFillMode=None
        self.lastCryoTemperature=None
        self.lastMacroResult={} #None
        self.lastWavelength=None
        self.lastDetDistPos=None
        self.lastResPos=None
        self.lastTransmission=None
        self.lastImageIntensity=None

        self.mxlocalParameters = {}

        self.waiting4UserCentring=None
        self.waiting4AutoCentring=None

        self.currentCentringStatus=None

        # Read the configuration file and setup the HO
        if self.getProperty('specversion') is None:
            logging.getLogger("HWR").error('DataCollect: you must specify a spec version')
            print 'self.configOk problem possibility 2'
            self.configOk=False
        else:
            if isConsoleApplication():
                self.continueCollect=PyCondition()
            else:
                self.continueCollect=QtCondition()

            # Get mandatory spec commands
            for prop_name in DataCollectPX2.MANDATORY_PROPS:
                desc=DataCollectPX2.MANDATORY_PROPS[prop_name]
                prop=self.getProperty(prop_name)
                print 'Debug 12.09.2012 MANDATORY_PROPS MS', prop_name, prop
                if prop is None:
                    logging.getLogger("HWR").error("DataCollect: you must specify the %s property in the xml configuration" % desc)
                    print 'self.configOk problem possibility 3'
                    self.configOk=False
                exec("self.%sProp=prop" % prop_name)

            # Get optional spec commands
            for prop_name in DataCollectPX2.OPTIONAL_PROPS:
                desc=DataCollectPX2.OPTIONAL_PROPS[prop_name]
                prop=self.getProperty(prop_name)
                print 'Debug 12.09.2012 OPTIONAL_PROPS MS', prop_name, prop
                if prop is None:
                    logging.getLogger("HWR").warning("DataCollect: you could specify the optional %s property in the xml configuration" % desc)
                exec("self.%sProp=prop" % prop_name)

            # Get mandatory spec channels
            for chan in DataCollectPX2.MANDATORY_CHANNELS:
                desc=DataCollectPX2.MANDATORY_CHANNELS[chan]
                try:
                    channel=self.getChannelObject(chan)
                except KeyError:
                    channel=None
                if channel is None:
                    logging.getLogger("HWR").error("DataCollect: you must specify the %s spec channel" % desc)
                    print 'self.configOk problem possibility 4'
                    self.configOk=False
                else:
                    try:
                        exec("self.connect(channel,'update',self.%sUpdate)" % chan)
                    except AttributeError:
                        pass
                print 'Debug 12.09.2012 MANDATORY_CHANNELS', chan, desc
                exec("self.%sChannel=channel" % chan)

            # Get optional spec channels
            for chan in DataCollectPX2.OPTIONAL_CHANNELS:
                desc=DataCollectPX2.OPTIONAL_CHANNELS[chan]
                try:
                    channel=self.getChannelObject(chan)
                except KeyError:
                    channel=None
                if channel is None:
                    logging.getLogger("HWR").warning("DataCollect: you should specify the %s spec channel" % desc)
                else:
                    try:
                        exec("self.connect(channel,'update',self.%sUpdate)" % chan)
                    except AttributeError:
                        pass
                exec("self.%sChannel=channel" % chan)

            # Load mandatory hardware objects
            for ho in DataCollectPX2.MANDATORY_HO:
                desc=DataCollectPX2.MANDATORY_HO[ho]
                name=self.getProperty(ho)
                print 'Debug 12.09.2012 MANDATORY_HO MS', prop_name, prop
                if name is None:
                    logging.getLogger("HWR").error('DataCollect: you must specify the %s hardware object' % desc)
                    hobj=None
                    print 'self.configOk problem possibility 5'
                    self.configOk=False
                else:
                    hobj=HardwareRepository.HardwareRepository().getHardwareObject(name)
                    if hobj is None:
                        logging.getLogger("HWR").error('DataCollect: invalid %s hardware object' % desc)
                        print 'self.configOk problem possibility 6'
                        self.configOk=False
                exec("self.%sHO=hobj" % ho)

            # Load optional hardware objects
            for ho in DataCollectPX2.OPTIONAL_HO:
                desc=DataCollectPX2.OPTIONAL_HO[ho]
                name=self.getProperty(ho)
                if name is None:
                    logging.getLogger("HWR").warning('DataCollect: you should specify the %s hardware object' % desc)
                    hobj=None
                else:
                    hobj=HardwareRepository.HardwareRepository().getHardwareObject(name)
                    if hobj is None:
                        logging.getLogger("HWR").error('DataCollect: invalid %s hardware object' % desc)
                exec("self.%sHO=hobj" % ho)

            # Parse mandatory commands


            # Connect signals 
            # Commented MS 12.09.2012
            if self.configOk:
                #self.macroCollectCmd.connectSignal("connected", self.connected)
                #self.macroCollectCmd.connectSignal("disconnected", self.disconnected)
                #self.macroCollectCmd.connectSignal('commandReady',self.cmdReady)
                #self.macroCollectCmd.connectSignal('commandNotReady',self.cmdNotReady)

                if self.machcurrentHO is not None:
                    self.connect(self.machcurrentHO,qt.PYSIGNAL('valueChanged'),self.machCurrentChanged)

                if self.cryostreamHO is not None:
                    self.connect(self.cryostreamHO,qt.PYSIGNAL("temperatureChanged"), self.cryoTemperatureChanged)

                if self.energyscanHO is not None:
                    self.connect(self.energyscanHO,qt.PYSIGNAL('energyChanged'),self.energyChanged)

                if self.detdistmotorHO is not None:
                    try:
                        self.connect(self.detdistmotorHO,qt.PYSIGNAL('positionChanged'),self.detdistmotorChanged)
                    except:
                        logging.getLogger("HWR").exception('DataCollect: problem connecting to the detector distance motor')

                if self.resmotorHO is not None:
                    try:
                        self.connect(self.resmotorHO,qt.PYSIGNAL('positionChanged'),self.resmotorChanged)
                    except:
                        logging.getLogger("HWR").exception('DataCollect: problem connecting to the resolution motor')

                if self.transmissionHO is not None:
                    self.connect(self.transmissionHO,qt.PYSIGNAL('attFactorChanged'),self.transmissionFactorChanged)

                self.phiMotor=None
                if self.minidiffHO is not None:
                    self.connect(self.minidiffHO,qt.PYSIGNAL('centringAccepted'),self.minidiffCentringAccepted)

                    self.phiMotor=self.minidiffHO.getDeviceByRole('phi')
                    if self.phiMotor is not None:
                        try:
                            self.connect(self.phiMotor,qt.PYSIGNAL('positionChanged'),self.phiMotorMoved)
                        except:
                            logging.getLogger("HWR").exception('DataCollect: problem connecting to the phi motor')

                # Get beamline configuration
                try:
                    bcm_pars=self.mxlocalHO["BCM_PARS"]
                    try:
                        self.mxlocalParameters["default_exposure_time"] = float(bcm_pars.getProperty("default_exposure_time"))
                    except:
                        pass
                    try:
                        self.mxlocalParameters["default_number_of_passes"] = int(bcm_pars.getProperty("default_number_of_passes"))
                    except:
                        pass
                    try:
                        self.mxlocalParameters["maximum_radiation_exposure"] = float(bcm_pars.getProperty("maximum_radiation_exposure"))
                    except:
                        pass
                    try:
                        self.mxlocalParameters["nominal_beam_intensity"] = float(bcm_pars.getProperty("nominal_beam_intensity"))
                    except:
                        pass
                    try:
                        self.mxlocalParameters["minimum_exposure_time"] = float(bcm_pars.getProperty("minimum_exposure_time"))
                        self.mxlocalParameters["minimum_phi_speed"] = float(bcm_pars.getProperty("minimum_phi_speed"))
                        self.mxlocalParameters["minimum_phi_oscillation"] = float(bcm_pars.getProperty("minimum_phi_oscillation"))
                        self.mxlocalParameters["maximum_phi_speed"] = float(bcm_pars.getProperty("maximum_phi_speed"))
                    except:
                        pass
                    self.mxlocalParameters["detector_extension"] = bcm_pars.getProperty("FileSuffix")
                    bcm_detector=bcm_pars["detector"]
                    self.mxlocalParameters["detector_type"] = bcm_detector.getProperty("type")
                    spec_pars=self.mxlocalHO["SPEC_PARS"]
                    spec_detector=spec_pars["detector"]
                    self.mxlocalParameters["detector_mode"] = int(spec_detector.getProperty("binning"))
                    beam=spec_pars["beam"]
                    self.mxlocalParameters["beam_ax"] = float(beam.getProperty("ax"))
                    self.mxlocalParameters["beam_ay"] = float(beam.getProperty("ay"))
                    self.mxlocalParameters["beam_bx"] = float(beam.getProperty("bx"))
                    self.mxlocalParameters["beam_by"] = float(beam.getProperty("by"))

                    inhouse_users=[]
                    try:
                        mxlocal_inhouse_users=self.mxlocalHO["INHOUSE_USERS"]
                    except:
                        logging.getLogger("HWR").warning('DataCollect: you should specify the inhouse users')
                    else:
                        try:
                            for el in mxlocal_inhouse_users:
                                try:
                                    proposal_code=el.code
                                except:
                                    pass
                                else:
                                    try:
                                        proposal_number=int(el.number)
                                    except:
                                        proposal_number=None
                                    inhouse_users.append((proposal_code,proposal_number))
                        except:
                            pass
                    self.mxlocalParameters['inhouse_users']=inhouse_users

                except:
                    logging.getLogger("HWR").exception('DataCollect: error reading parameters from mxlocal configuration file')
                    print 'self.configOk problem possibility 1'
                    self.configOk = False

                # Initialize state
                if self.emitCollectConnected():
                    self.emitCollectReady()

    def connectVisualisation(self):
        # For ADXV visu (PL 26_07_2011). MS 2013-06-19 coppied from DataCollectPX1.
        #os.system("killall adxv_follow")
        _cl = "gnome-terminal --window-with-profile=adxv --title AdxvFollow "
        _cl += " --geometry=100x30+1680+5 -e /home/experiences/proxima2a/com-proxima2a/MxCuBE/bin/adxv_follow &"
        
        def adxv_socket_running():
            return commands.getoutput('ps aux | grep adxv | grep socket').find('-socket') != -1
            
        if not adxv_socket_running():
            os.system(_cl)
            time.sleep(1.)
        
        adxv_host = '127.0.0.1'
        adxv_port = 9997
        
        #res = socket.getaddrinfo(adxv_host, adxv_port, 0, socket.SOCK_STREAM)
        #af, socktype, proto, canonname, sa = res[0]
        #self.persistentValues["adxv"] = socket.socket(af, socktype, proto)
        #self.persistentValues["adxv"].connect((adxv_host, adxv_port)) #(adxv_host, adxv_port))
        try:
            res = socket.getaddrinfo(adxv_host, adxv_port, 0, socket.SOCK_STREAM)
            af, socktype, proto, canonname, sa = res[0]
            self.persistentValues["adxv"] = socket.socket(af, socktype, proto)
            self.persistentValues["adxv"].connect((adxv_host, adxv_port)) #(adxv_host, adxv_port))
        except:
            self.persistentValues["adxv"] = None
            print "Warning: Can't connect to adxv for the following collect."
            

    """
    isConnected
        Description: Checks if spec is connected (the version running the collect macro)
        Type       : method
        Arguments  : none
        Returns    : bool; True is h.o. is configured OK and spec is running, otherwise False
    """
    def isConnected(self):
        if not self.configOk:
            return False
        #modified based on PX1 DataCollect file (M.S. 13.09.2012)
        try:
            #_state = self.md2.State()
            try:
                md2device = DeviceProxy(self.getProperty('md2')) #self.collectServer.State on PX1
                k = md2device.ping() #probably closer to what we want than the previous line (M.S. 13.09.2012)
            except:
                logging.getLogger("HWR").error("%s: unknown device name", self.getProperty('md2'))
                return False
            return True
        except Exception, err:
            print err
            return False
        #return self.macroCollectCmd.isSpecConnected()

    """
    disconnected
        Description: Called when spec is disconnected
        Type       : slot
        Arguments  : none
        Returns    : nothing
        Signals    : collectDisconnected
        Notes      : Sometimes called explicitly
    """
    def disconnected(self):
        if not self.globalLock.locked():
            try:
                ended_running=self.threadRefs["endedActions"].aliveAndKicking()
            except (KeyError,AttributeError):
                ended_running=False
            if ended_running:
                self.threadRefs["endedActions"].respect()
            else:
                try:
                    failed_running=self.threadRefs["failedActions"].aliveAndKicking()
                except (KeyError,AttributeError):
                    failed_running=False
                if failed_running:
                    self.threadRefs["failedActions"].respect()

        self.lastReady=None
        self.lastConnected=None
        self.guiEmit('collectDisconnected', ())


    """
    connected
        Description: Called when spec is connected
        Type       : slot & method
        Arguments  : none
        Returns    : nothing
        Signals    : collectConnected
        Notes      : Sometimes called explicitly
    """
    def connected(self):
        if self.lastConnected is True:
            return

        self.lastConnected=True
        self.guiEmit('collectConnected', ())

        self.lastReady=None
        if self.energyscanHO is not None:
            try:
                curr_energy=self.energyscanHO.getCurrentEnergy()
                curr_wavelength=self.energyscanHO.getCurrentWavelength()
            except:
                pass
            else:
                self.energyChanged(curr_energy,curr_wavelength)
        if self.detdistmotorHO is not None:
            try:
                self.detdistmotorChanged(float(self.detdistmotorHO.getPosition()))
            except:
                pass
        if self.resmotorHO is not None:
            try:
                self.resmotorChanged(float(self.resmotorHO.getPosition()))
            except:
                pass
        if self.transmissionHO is not None:
            try:
                self.transmissonFactorChanged(float(self.transmissionHO.getAttFactor()))
            except:
                pass

        if self.phiMotor is not None:
            try:
                self.phiMotorMoved(float(self.phiMotor.getPosition()))
            except:
                pass

    """
    emitCollectConnected
        Description : 
        Type        : method
        Arguments   : none
        Returns     : bool; True is spec is connected, otherwise False
        Signals     : collectConnected
    """
    def emitCollectConnected(self):
        conn=False
        if self.isConnected():
            self.connected()
            conn=True
        else:
            self.disconnected()
        return conn

    """
    isReady
        Description: Checks if the hardware object is ready to collect
        Type       : method
        Arguments  : none
        Returns    : bool; True is h.o. is configured, spec is ready, and there's no ongoing collection,
                     otherwise False
    """
    def isReady(self):
        #Modified M.S. 13.09.2012 based on DataCollect from PX1
        logging.getLogger("HWR").debug('DataCollect:  isReady ')
        try:
            md2device = DeviceProxy(self.getProperty('md2'))
        except:
            logging.getLogger("HWR").error("%s: unknown device name", self.getProperty('md2'))
        print 'self.isConnected()', self.isConnected()
        if self.isConnected():
            #if self.macroCollectCmd.isSpecReady():
            print 'md2.state()', md2device.state() 
            if md2device.state().name in ['STANDBY']:
                print 'self.globalLock.locked()', self.globalLock.locked()
                if not self.globalLock.locked(): # MS 17.09.2012, is globalLock.locked() False or True that we wnat? 
                #if self.globalLock.locked():
                    print "DataCollect: isReady OK"
                    return True
        return False

    """
    cmdReady
        Description: Called when spec is ready
        Type       : slot & method
        Arguments  : force (bool; =False)
        Returns    : nothing
        Signals    : collectReady(True)
        Notes      : Sometimes called explicitly with force=True
    """
    def cmdReady(self,force=False):
        if not self.globalLock.locked() or force:
            if self.lastReady!=True:
                self.lastReady=True
                self.guiEmit('collectReady', (True,))

    """
    cmdNotReady
        Description: Called when spec is not ready
        Type       : slot & method
        Arguments  : force (bool; =False)
        Returns    : nothing
        Signals    : collectReady(False)
        Notes      : Sometimes called explicitly with force=True
    """
    def cmdNotReady(self,force=False):
        if not self.globalLock.locked() or force:
            if self.lastReady!=False:
                self.lastReady=False
                self.guiEmit('collectReady', (False,))

    """
    emitCollectReady
        Description: 
        Type       : method
        Arguments  : force (bool; =False)
        Returns    : bool; True is the h.o. is spec is ready, otherwise False
        Signals    : collectReady
    """
    def emitCollectReady(self,force=False):
        # MS 14.09.2012. we're not using macroCollect. Let's use md2 state instead.
        ready=False
        #if self.macroCollectCmd.isSpecReady():
        try:
            md2device = DeviceProxy(self.getProperty('md2'))
        except:
            logging.getLogger("HWR").error("%s: unknown device name", self.getProperty('md2'))

        if md2device.State().name in ['STANDBY', 'OFF']:
            if self.lastConnected is None:
                if self.isConnected():
                    self.connected()
            self.cmdReady(force=force)
            ready=True
        else:
            self.cmdNotReady(force=force)
        return ready

    """
    setBrick
        Description: 
        Type       : method
        Arguments  : brick (instance; expects a BlissWidget/QWidget object)
        Returns    : nothing
    """
    def setBrick(self,brick):
        if not isConsoleApplication():
            self.Brick=brick

    """
    machCurrentChanged
        Description: Called when a machine parameter changes; keeps the machine parameters
                     in the object instance for later use
        Type       : slot
        Arguments  : value    (float)
                     opmsg    (string)
                     fillmode (string)
                     opmsg    (string)
                     refill   (int; not used)
        Returns    : nothing
    """
    def machCurrentChanged(self,value=None,opmsg=None,fillmode=None,refill=None):
        if value is not None:
            self.lastMachineCurrent=value
        if opmsg is not None:
            self.lastMachineMessage=opmsg
        if fillmode is not None:
            self.lastMachineFillMode=fillmode

    """
    cryoTemperatureChanged
        Description: Called when a cryo temperature changes; keeps it for later use
        Type       : slot
        Arguments  : temp       (float)
                     temp_error (string; not used)
        Returns    : nothing
    """
    def cryoTemperatureChanged(self,temp,temp_error=None):
        try:
            t = float(temp)
        except TypeError:
            self.lastCryoTemperature=None
        else:
            self.lastCryoTemperature=t

    """
    energyChanged
        Description: Called when the energy changes; keeps it for later use
        Type       : slot
        Arguments  : energy     (float)
                     wavelength (float; not used)
        Returns    : nothing
    """
    def energyChanged(self,energy,wavelength):
        self.lastWavelength=wavelength

    """
    detdistmotorChanged
        Description: Called when the detector distance changes; keeps it for later use
        Type       : slot
        Arguments  : detdist_pos (float)
        Returns    : nothing
    """
    def detdistmotorChanged(self,detdist_pos):
        self.lastDetDistPos=detdist_pos

    """
    resmotorChanged
        Description: Called when the resolution motor changes; keeps it for later use
        Type       : slot
        Arguments  : res_pos (float)
        Returns    : nothing
    """
    def resmotorChanged(self,res_pos):
        self.lastResPos=res_pos

    """
    transmissionFactorChanged
        Description: Called when the transmission changes; keeps it for later use
        Type       : slot
        Arguments  : trans (float)
        Returns    : nothing
    """
    def transmissionFactorChanged(self,trans):
        #Added logging (MS 13.09.2012), sync with PX1
        logging.getLogger("HWR").debug('DataCollect:  transmissionFactorChanged ')
        self.lastTransmission=trans

    """
    phiMotorMoved
        Description: Called when the phi motor positons changes; keeps it for later use
        Type       : slot
        Arguments  : pos (float)
        Returns    : nothing
        Signals    : collectAxisMotorMoved
    """
    def phiMotorMoved(self,pos):
        #Added logging (MS 13.09.2012), sync with PX1
        logging.getLogger("HWR").debug('DataCollect:  phiMotorMoved ')
        self.guiEmit('collectAxisMotorMoved', (pos,))

    """
    getAxisPosition
        Description: Returns the current axis/phi motor position
        Type       : method
        Arguments  : none
        Returns    : float; phi motor user position
    """
    def getAxisPosition(self):
        #Added logging (MS 13.09.2012), sync with PX1
        logging.getLogger("HWR").debug('DataCollect:  getAxisPosition ')
        pos=None
        if self.configOk and self.phiMotor is not None:
            try:
                pos=float(self.phiMotor.getPosition())
            except:
                pos=None
        return pos

    """
    collectEvent
        Description: Posts an event in the previously defined brick (with setBrick) event queue
        Type       : method
        Arguments  : method    (python function; method to be called)
                     arguments (tuple/list; arguments for the above python function)
        Returns    : none
    """
    def collectEvent(self,method,arguments):
        postCollectGUIEvent(self.Brick,method,arguments)

    """
    guiEmit
        Description: Wrapper to emit a signal: if the application is a console application
                     then the standard python emit is used; otherwise due to Qt threads
                     the method is posted to the previously defined brick
        Type       : method
        Arguments  : signal    (string; signal name)
                     arguments (tuple/list; arguments for the signal)
        Returns    : none
        Signals    : the signal parameter...
    """
    def guiEmit(self,signal,params):
        #if isConsoleApplication():
            #self.emit(signal,params)
        #else:
        self.collectEvent(self.emit,(signal,params))

    """
    getBeamlineConfiguration
        Description: Returns the beamline configuration (read from mxlocal.xml).
        Type       : method
        Arguments  : keys (tuple/list; a list of the keys of the wanted configuration)
        Returns    : dict; a dictionary where the keys are the argument list, and the
                     values the repective beamline configuration
        Exceptions : KeyError
        Keys       : default_exposure_time,default_number_of_passes,maximum_radiation_exposure,
                     nominal_beam_intensity,minimum_exposure_time,minimum_phi_speed,
                     minimum_phi_oscillation,maximum_phi_speed,detector_extension,detector_type,
                     detector_mode,beam_ax,beam_ay,beam_bx,beam_by,inhouse_users
    """
    def getBeamlineConfiguration(self,keys):
        if keys is None:
            return dict(self.mxlocalParameters)
        d={}
        for key in keys:
            d[key]=self.mxlocalParameters[key]
        return d

    """
    getBeamlineCurrentParameters
        Description: Returns the beamline current parameters (energy, etc.).
        Type       : method
        Arguments  : keys (tuple/list; a list of the keys of the wanted parameters)
        Returns    : dict; a dictionary where the keys are the argument list, and the
                     values the repective beamline configuration
        Exceptions : KeyError
        Keys       : resolution,detdistance,wavelength,intensity
    """
    def getBeamlineCurrentParameters(self,keys):
        #Added logging (MS 13.09.2012), sync with PX1
        logging.getLogger("HWR").debug('DataCollect:  getBeamlineCurrentParameters ')
        d={}
        for key in keys:
            if key=="resolution" and self.lastResPos is not None:
                d[key]=self.lastResPos
            elif key=="detdistance" and self.lastDetDistPos is not None:
                d[key]=self.lastDetDistPos
            elif key=="wavelength" and self.lastWavelength is not None:
                d[key]=self.lastWavelength
            elif key=="intensity" and self.lastImageIntensity is not None:
                d[key]=self.lastImageIntensity
            else:
                logging.getLogger("HWR").debug("DataCollect: raising KeyError for %s" % key)
                raise KeyError
        return d

    """
    calculateBeamCentre
        Description: Calculates the beam centre using the beamline configuration.
        Type       : method
        Arguments  : none
        Returns    : dict (or None if error); keys=("x","y")
        Notes      : There's a spec macro that does the same thing.
    """
    def calculateBeamCentre(self):
        #Added logging (MS 13.09.2012), sync with PX1
        logging.getLogger("HWR").debug('DataCollect:  calculateBeamCentre ')
        d=None
        if self.configOk and self.lastDetDistPos is not None:
            d={}
            try:
                d['x']=self.mxlocalParameters['beam_ax']*self.lastDetDistPos + self.mxlocalParameters['beam_bx']
                d['y']=self.mxlocalParameters['beam_ay']*self.lastDetDistPos + self.mxlocalParameters['beam_by']
            except:
                logging.getLogger("HWR").exception("DataCollect: problem calculating beam centre")
                d=None
        return d

    """
    calculateBeamSize
        Description: Calculates the beam size using the slitbox h.o.
        Type       : method
        Arguments  : none
        Returns    : dict (or None if error); keys=("x","y")
    """
    def calculateBeamSize(self):
        #Added logging (MS 13.09.2012), sync with PX1 (the routine commented in the default code - probably a bug)
        logging.getLogger("HWR").debug('DataCollect: calculateBeamSize')
        d=None
        if self.configOk:
            if self.minidiffHO is None or self.slitboxHO is None:
                pass
            else:
                s1v = self.slitboxHO.getDeviceByRole('s1v')
                s2v = self.slitboxHO.getDeviceByRole('s2v')
                s1h = self.slitboxHO.getDeviceByRole('s1h')
                s2h = self.slitboxHO.getDeviceByRole('s2h')
                if s1v is None or s2v is None or s1h is None or s2h is None:
                    pass
                else:
                    try:
                        s1vp = float(s1v.getPosition())
                        s2vp = float(s2v.getPosition())
                        s1hp = float(s1h.getPosition())
                        s2hp = float(s2h.getPosition())
                    except:
                        logging.getLogger("HWR").exception("DataCollect: problem calculating beam size")
                    else:
                        sv = min(s1vp, s2vp)
                        sh = min(s1hp, s2hp)
                        d={'x':sh,'y':sv}
        return d
    

    """
    collectLog
        Description: Logs one or several messages using the python logging module (if the
                     level is not None). Also if a data collection is ongoing, writes those
                     same messages (except if the level is "debug") in its log file.
        Type       : method
        Arguments  : msg   (string or list/tuple of strings; the message(s) to be logged)
                     level (string; ="info"; which log level to use)
        Returns    : nothing
    """
    def collectLog(self,msg,level="info"):
        log_file=self.persistentValues["logFile"]
        curr_time=time.strftime("%Y-%m-%d %H:%M:%S")
                
        if type(msg)==types.TupleType or type(msg)==types.ListType:
            if log_file is not None and level!="debug":
                lines=[]
                for m in msg:
                    lines.append("[%s] %s\r\n" % (curr_time,m.capitalize()))
                try:    
                    log_file.writelines(lines)
                except:
                    pass
            if level is not None:
                exec("log_fun=logging.getLogger('HWR').%s" % level)
                for m in msg:
                    if level=="debug":
                        log_msg="DataCollect: %s" % m
                    else:
                        log_msg=m.capitalize()
                    log_fun(log_msg)
        elif type(msg)==types.StringType:
            if log_file is not None and level!="debug":
                try:
                    log_file.write("[%s] %s\r\n" % (curr_time,msg.capitalize()))
                except:
                    pass
            if level is not None:
                if level=="debug":
                    log_msg="DataCollect: %s" % msg
                else:
                    log_msg=msg.capitalize()
                exec("log_fun=logging.getLogger('HWR').%s" % level)
                log_fun(log_msg)

    """
    isSearchDone
        Description: Checks if the hutch has been searched
        Type       : method
        Arguments  : none
        Returns    : bool; True if the hutch was searched, False if not or if the safety
                     shutter is disabled/moving/unknown/fault/etc.
    """
    def isSearchDone(self):
        #It seems this method is not used on PX1. It might be made usable by making use of pss_exp device instead of safetyshutterHO 
        if self.safetyshutterHO is not None:
            if self.safetyshutterHO.getShutterState() in ('disabled','fault','error','moving','unknown'):
                return False
        return True

    """
    setCentringStatus
        Description: Keeps track of the Minidiff centring status. Not connected to any
                     signal: this method must be explicitly called everytime the centring
                     status changes!
        Type       : method
        Arguments  : centring_status (dict; from the Minidiff h.o.)
        Returns    : nothing
    """
    def setCentringStatus(self,centring_status):
        #Added logging (MS 13.09.2012), sync with PX1
        logging.getLogger("HWR").debug('DataCollect:  setCentringStatus ')
        if not self.configOk:
            logging.getLogger("HWR").error("DataCollect: not properly configured")
            return
        if self.globalLock.locked():
            logging.getLogger("HWR").debug("DataCollect: setCentringStatus is discarted while collection...")
            return
        self.currentCentringStatus=centring_status

    """
    prepareParameters4Collect
        Description: Logs the collections arguments; sets the template and fileame suffix/extension
                     in the arguments; sets the dark parameter if it's the first data collection;
                     uses the default_number_of_passes from the configuration if none is given; creates
                     the directory.
        Type       : method
        Arguments  : arguments (dict; the collection parameters dictionary, based on the DNA XSD class 
                                Collect_request)
        Returns    : tuple ([0]=bool; result of the actions, True if OK, False if error
                            [1]=string or dict; if [0]==True then it's the oscillation_sequence
                                key of the parameters; if [0]==False then it's the string error
                                message)
    """
    def prepareParameters4Collect(self,arguments):
        #Added logging (MS 13.09.2012), sync with PX1
        logging.getLogger("HWR").debug('DataCollect: prepareParameters4Collect')
        try:
            centred_images=arguments["centring_status"]["images"]
        except:
            centred_images=None
        else:
            if centred_images is not None:
                arguments["centring_status"]["images"]="..."
        #self.collectLog("preparing the parameters... (%s)" % arguments,"debug")
        
        ### here comes a lot of code in the case of DataCollect on PX1. 
        
        '''The code takes care of detector protection, removal of fluorescence detector and light and beamstop insertion.
        
        For PX2 it's not yet necessary. (M.S. 13.09.2012)
        '''
        
        ### and here it ends
        
        if centred_images is not None:
            arguments["centring_status"]["images"]=centred_images

        try: # Just to make sure...
            arguments.pop('centred_pos')
        except:
            pass

        if self.collectionHistory==0:
            arguments['dark']='1'
        self.collectionHistory+=1

        try:
            osc_seq=arguments["oscillation_sequence"] #arguments["oscillation_sequence"][0]['start_image_number']
            if len(osc_seq)==0:
                raise KeyError
            elif len(osc_seq)>1:
                return (False,"multiple oscillation sequences not implemented!")
        except KeyError:
            return (False,"oscillation sequence not found!")

        try:
            int(osc_seq[0]['number_of_passes'])
        except (KeyError,TypeError,ValueError):
            try:
                default_no_passes=int(self.mxlocalParameters['default_number_of_passes'])
            except (KeyError,TypeError,ValueError):
                self.collectLog("no default number of passes, using 1","warning")
                default_no_passes=1
            osc_seq[0]['number_of_passes']=default_no_passes

        #This is commented on PX1. Let's try to leave for now.
        #Udate 14.09. 2012. No, let's rather follow in the footsteps of the great men before us.
        #if self.argumentsChannel is None:
            #return (False,"invalid arguments spec channel!")

        try:
            file_suffix=self.mxlocalParameters['detector_extension']
        except KeyError:
            return (False,"error getting detector filename extension!")
        arguments['fileinfo']['suffix']=file_suffix

        # Build file template 
        # Here the current version differ from PX1, but seems to be doing the right thing. Leaving unchanged (MS 13.09.2012).
        image_number_format="####"
        try:
            file_prefix=arguments['fileinfo']['prefix']
        except KeyError:
            file_prefix=""
        try:
            run_number=str(arguments['fileinfo']['run_number'])
        except KeyError:
            run_number="1"
        
        arguments['fileinfo']['template']="%s_%s_%s.%s" %\
            (file_prefix,run_number,image_number_format,file_suffix)

        directory=arguments['fileinfo']['directory']
        if not os.path.isdir(directory):
            self.collectLog("creating directory %s" % directory)
            try:
                makedirsRetry(directory)
            except OSError,diag:
                return (False,"error creating directory %s! (%s)" % (directory,str(diag)))
        process_dir = arguments['fileinfo']['process_directory']
        if not os.path.isdir(process_dir):
            self.collectLog("creating process directory %s" % process_dir)
            try:
                makedirsRetry(process_dir)
            except OSError,diag:
                return (False,"error creating process directory %s! (%s)" % (process_dir,str(diag)))      
 
        ### use collectLog to store the collection parameters in the collect log file
        self.collectLog("directory=%s" % directory,None)
        self.collectLog("prefix=%s" % file_prefix,None)
        self.collectLog("run number=%s" % run_number,None)
        self.collectLog("first image=%s" % osc_seq[0]['start_image_number'],None)
        self.collectLog("number of images=%s" % osc_seq[0]['number_of_images'],None)
        self.collectLog("oscillation start=%s degrees" % osc_seq[0]['start'],None)
        self.collectLog("oscillation range=%s degrees" % osc_seq[0]['range'],None)
        self.collectLog("overlap=%s degrees" % osc_seq[0]['overlap'],None)
        self.collectLog("exposure time=%s seconds" % osc_seq[0]['exposure_time'],None)
        self.collectLog("number of passes=%s" % osc_seq[0]['number_of_passes'],None) #This line is commented out on PX1 (MS 13.09.2012)
        try:
            self.collectLog("exposure mode=%s" % arguments['experiment_type'],None)
        except KeyError:
            pass
        # Following try/except clause is commented out on PX1 (MS 13.09.2012)
        try:
            det_mode=int(arguments['detector_mode'])
            modes=("software binned","unbinned","hardware binned", "disable")
            self.collectLog("detector mode=%s" % modes[det_mode],None)
        except (KeyError,IndexError,ValueError,TypeError):
            pass
        try:
            self.collectLog("comments=%s" % arguments['comment'],None)
        except KeyError:
            pass
        
        # PL. Create a directory with write permission for users data-processing.
        try:
            make_process_dir(directory)
            write_goimg(os.path.join(directory, "process"))
        except:
            print "Error. Can't creat the process directory in %s." % directory
            
        return (True,osc_seq)

    """
    prepareDatabase4Collect
        Description: Adds extra parameters in the arguments from the current beamline state: beam size,
                     fill mode; stores the parameters in a new entry in the DataCollection table.
        Type       : method
        Arguments  : arguments (dict; the collection parameters dictionary, based on the DNA XSD class 
                                Collect_request)
        Returns    : tuple ([0]=bool; result of the actions, True if OK, False if error
                            [1]=string or dict; if [0]==True then it's the data collection entry id
                                in the database; if [0]==False then it's the string error message)
        Threading  : Due to updating the database, the time to finish is unknown; might block the calling 
                     thread while waiting for a HTTP timeout
    """
    def prepareDatabase4Collect(self,arguments):
        self.collectLog("preparing the database...","debug")

        start_time=time.strftime("%Y-%m-%d %H:%M:%S")
        self.persistentValues["arguments"]["collection_start_time"]=start_time
        
        # The following four lines were commented out in the pristine source of DataCollect, it's in place on PX1 though. Uncommenting (MS 13.09.2012)
        beam_size=self.calculateBeamSize()
        if beam_size is not None:
           arguments["slit_gap_hor"]=beam_size['x']
           arguments["slit_gap_ver"]=beam_size['y']

        arguments["synchrotron_mode"]=self.lastMachineFillMode

        state=True
        id_or_msg=None
        try:
            int(arguments['sessionId'])
        except:
            logging.getLogger().warning("Data Collection has no sessionId information. It can not be stored in the database.") #just pass on PX1
        else:
            if self.dbserverHO is None:
                state=False
                id_or_msg="invalid DB Server! (data collection not inserted)"
            else:
                db_answer=self.dbserverHO.storeDataCollection(arguments,self.mxlocalHO)
                try:
                    db_code=db_answer['code']
                except KeyError:
                    self.collectLog("error storing the data collection, unknown result code!","error")
                else:
                    if db_code=='ok':
                        try:
                            id_or_msg=int(db_answer['dataCollectionId'])
                        except:
                            self.collectLog("error storing the data collection, no id returned!","error")
                            id_or_msg=None
        
        # Sync with PX1 for the following line. PL. 31/01/2011. Temporary change of id_or_msg. No db setup for now.
        id_or_msg = 1
        return (state,id_or_msg)

    """
    prepareSampleChanger4Collect
        Description: Gets the blsampleid, barcode and sample location from the parameters. If there's
                     a barcode or location it tries to load that sample. If the sample is already there
                     returns immediately (returning [0] as True). If loading the sample and there's also
                     a blsampleid it reads the sample information from the database to get the correct
                     holder length and the last centred position. Tries 3 times to load the sample.
        Type       : method
        Arguments  : arguments (dict; the collection parameters dictionary, based on the DNA XSD class 
                                Collect_request)
        Returns    : tuple ([0]=bool; result of the actions, True if OK, False if error
                            [1]=string or tuple or None; if [0]==False then it's the string error message
                                if [0]==True then it's either the sample barcode as a string or the
                                sample location as a tuple (basket,vial) or None if the sample is not
                                inside the sample changer
                            [2]=None or float; only exists if the sample is inside the sample changer:
                                the loading holder length
                            [3]=bool; only exists if the sample is inside the sample changer: True if the
                                      sample was already loaded, False if the sample had to be loaded)
        Threading  : Due to fetching data from the database, the time to finish is unknown; might block
                     the calling thread while waiting for a HTTP timeout. Also if waiting for the sample
                     changer to load the sample blocks the calling thread on the self.continueCollect
                     condition object.
        Signals    : collectMountingSample
    """
    def prepareSampleChanger4Collect(self,arguments):
        # Added logging, sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  prepareSampleChanger4Collect ') 
        self.collectLog("preparing the sample changer...","debug")

        try:
            blsampleid=int(arguments['sample_reference']['blSampleId'])
        except (KeyError,ValueError,TypeError):
            blsampleid=None

        # Load a sample using the sample changer
        try:
            sample_code=str(arguments['sample_reference']['code'])
        except KeyError:
            sample_code=None
        else:
            if sample_code=="":
                sample_code=None

        sample_location=None
        #if sample_code is None:
        try:
            basket_number=int(arguments['sample_reference']['container_reference'])
        except (KeyError,ValueError,TypeError):
            basket_number=None
        else:
            try:
                vial_number=int(arguments['sample_reference']['sample_location'])
            except (KeyError,ValueError,TypeError):
                vial_number=None
            else:
                sample_location=(basket_number,vial_number)

        holder_length=None

        if sample_code is not None or sample_location is not None:
            if self.samplechangerHO is None:
                self.guiEmit('collectMountingSample', (sample_code,sample_location,False))
                return (False,"invalid sample changer hardware object; unable to mount the sample %s/%s!" % (sample_code,str(sample_location)))

            sc_can_load=self.samplechangerHO.canLoadSample(sample_code,sample_location)
            if not sc_can_load[0]:
                self.guiEmit('collectMountingSample', (sample_code,sample_location,False))
                return (False,"sample changer hardware object denies mounting the sample %s/%s!" % (sample_code,str(sample_location)))

            if sc_can_load[1]:
                holder_length=self.samplechangerHO.getLoadedHolderLength()
                if sample_code is None:
                    sample_code=sample_location
                return (True,sample_code,holder_length,True)

            motors_pos_dict={}
            db_answer={}
            # Get info about the sample (holder length and last known centring motors position)
            if blsampleid is not None:
                if self.dbserverHO is not None:
                    db_answer=self.dbserverHO.getBLSample(blsampleid)

                    # Get last known centring position
                    try:
                        last_known_pos=str(db_answer['lastKnownCenteringPosition'])
                    except KeyError:
                        self.collectLog("no last known centred position","debug")
                    else:
                        last_known_pos_list=last_known_pos.split()
                        for motor_name_pos in last_known_pos_list:
                            try:
                                motor_name,motor_pos=motor_name_pos.split('=')
                            except ValueError:
                                self.collectLog("invalid last known centred position (%s)" % last_known_pos,"debug")
                                motors_pos_dict={}
                                break
                            else:
                                try:
                                    motors_pos_dict[str(motor_name)]=float(motor_pos)
                                except (ValueError,TypeError):
                                    self.collectLog("invalid last known centred motor position (%s=%s)" % (motor_name,motor_pos),"debug")
                                    motors_pos_dict={}
                                    break

                        if motors_pos_dict:
                            try:
                                last_known_pos_id=int(motors_pos_dict.pop('sessionId'))
                            except (KeyError,ValueError,TypeError):
                                self.collectLog("invalid session in positions (%s)" % last_known_pos,"debug")
                                motors_pos_dict={}
                            else:
                                try:
                                    session_id=int(self.persistentValues['arguments']['sessionId'])
                                except (ValueError,TypeError,KeyError),ex:
                                    self.collectLog("invalid current session (%s)" % str(ex),"debug")
                                    motors_pos_dict={}
                                else:
                                    if last_known_pos_id!=session_id:
                                        self.collectLog("different session of last known centred position","debug")
                                        motors_pos_dict={}
                                    else:
                                        self.collectLog("previous centred position: %s" % last_known_pos,"debug")
                else:
                    self.collectLog("database not configured, unable to get sample info!","warning")

            """
            # talk to bernard: is blsampleid (used inside spec) still necessary?
            if self.samplechangerHO is not None:
                if self.samplechangerHO.isMicrodiff():
                    if blsampleid is not None:
                        motors_pos_dict["blsampleid"]=blsampleid
            """

            # Find out the holder length
            try:
                holder_length=float(arguments['sample_reference']['holderLength'])
            except KeyError:
                try:
                    holder_length=float(db_answer['holderLength'])
                except KeyError:
                    self.collectLog("missing holder length in database, using default of 22.0!","warning")
                    holder_length=22.0
                except ValueError:
                    self.collectLog("invalid holder length in database (%s), using default of 22.0!" % holder_length,"warning")
                    holder_length=22.0
            except ValueError:
                self.collectLog("invalid holder length (%s), using default of 22.0!" % holder_length,"warning")
                holder_length=22.0
            arguments['sample_reference']['holderLength']=holder_length

            # Remove all centring information if loading sample
            try:
                arguments.pop('centring_status')
            except:
                pass

            self.guiEmit('collectMountingSample', (sample_code,sample_location,None))
            if sample_code is not None:
                self.collectLog("mounting the sample %s" % sample_code)
            else:
                self.collectLog("mounting the sample %s" % str(sample_location))
            tries=DataCollectPX2.LOADSAMPLE_TRIES
            while tries>0:
                self.continueCollect.reset()
                self.collectEvent(self.samplechangerHO.loadSample,(holder_length,sample_code,sample_location,self.sampleLoaded,self.loadSampleFailed,None,motors_pos_dict))
                self.collectLog("waiting for the sample to be mounted on the axis...")
                res=self.continueCollect.Zzz(DataCollectPX2.LOADSAMPLE_TIMEOUT)
                if res==CollectCondition.HARD_ABORT:
                    self.guiEmit('collectMountingSample', (sample_code,sample_location,False))
                    return (False,"sample mounting aborted!")
                elif res==CollectCondition.SOFT_ABORT:
                    self.guiEmit('collectMountingSample', (sample_code,sample_location,False))
                    return (None,"sample mounting aborted!")
                elif res==CollectCondition.RETRY:
                    tries-=1
                    if tries==0:
                        self.guiEmit('collectMountingSample', (sample_code,sample_location,False))
                        return (None,"unable to mount the sample!")
                    self.collectLog("retrying to mount the sample!","warning")
                elif res==CollectCondition.PROCEED:
                    tries=0
                else:
                    if res==CollectCondition.TIMEOUT:
                        self.collectLog("timeout mounting the sample!","error")
                    self.guiEmit('collectMountingSample', (sample_code,sample_location,False))
                    return (False, "unable to mount the sample!")

            self.guiEmit('collectMountingSample', (sample_code,sample_location,True))

        if sample_code is None:
            sample_code=sample_location
        return (True,sample_code,holder_length,False)

    """
    prepareSample4Collect
        Description: If the sample was loaded then it requests a centring. Otherwise it sets
                     the arguments centring status using the last set (unless it was already
                     set in the arguments).
        Type       : method
        Arguments  : sample_was_loaded (bool; if the sample was loaded, thus requiring centring)
                     arguments         (dict; the collection parameters dictionary, based on the DNA
                                        XSD class Collect_request)
        Returns    : tuple ([0]=bool; result of the actions, True if OK, False if error
                            [1]=string; if [0]==False then it's the string error message, if [0]==True
                            then it does not exist!)
        Threading  : If waiting for a centring, blocks the calling thread on the self.continueCollect
                     condition object.
        Signals    : collectValidateCentring,collectRejectCentring
    """
    def prepareSample4Collect(self,sample_was_loaded,arguments):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  prepareSample4Collect ')
        def cancelAndContinue():
            arguments["centring_status"]={"valid":False}

            self.continueCollect.reset()
            self.collectLog("trying to cancel the centring")

            if self.waiting4AutoCentring:
                self.minidiffHO.cancelCentringMethod(reject=True)
            else:
                self.guiEmit('collectRejectCentring', ())
                if DataCollectPX2.CENTRING_CANCELLED_SLEEP==-1:
                    self.collectLog("waiting for the centring to stop...")
                    self.continueCollect.Zzz(DataCollectPX2.CANCELCENTRE_TIMEOUT)
                else:
                    time.sleep(DataCollectPX2.CENTRING_CANCELLED_SLEEP)

            self.waiting4UserCentring=False
            self.waiting4AutoCentring=False

        self.collectLog("preparing the sample...","debug")

        try:
            blsampleid=int(arguments['sample_reference']['blSampleId'])
        except (KeyError,ValueError,TypeError):
            blsampleid=None

        try:
            start_auto_centring=str(arguments['start_auto_centring']).upper()=="TRUE"
        except:
            start_auto_centring=False

        if sample_was_loaded:
            # Centre the sample
            self.collectLog("waiting for sample centring...")

            self.continueCollect.reset()

            if start_auto_centring:
                self.waiting4AutoCentring=True
                self.waiting4UserCentring=False
                sample_info={}
                if blsampleid is not None:
                    sample_info["blsampleid"]=blsampleid
                self.minidiffHO.simulateAutoCentring(sample_info=sample_info)
            else:
                self.waiting4UserCentring=True
                self.waiting4AutoCentring=False
                fileinfo=arguments['fileinfo']
                self.guiEmit('collectValidateCentring', (sample_was_loaded,fileinfo))

            res=self.continueCollect.Zzz(DataCollectPX2.CENTRESAMPLE_TIMEOUT)

            if res==CollectCondition.HARD_ABORT:
                cancelAndContinue()
                return (False,"sample centring aborted!")
            elif res==CollectCondition.SOFT_ABORT:
                cancelAndContinue()
                return (None,"sample centring aborted!")
            elif res==CollectCondition.PROCEED:
                pass
            else:
                if res==CollectCondition.TIMEOUT:
                    self.collectLog("timeout while waiting for sample centring!","error")
                    cancelAndContinue()
                return (None,"unable to centre the sample!")
        elif start_auto_centring:
                self.collectLog("waiting for sample centring...")
                self.continueCollect.reset()
                self.waiting4AutoCentring=True
                self.waiting4UserCentring=False
                sample_info={}
                if blsampleid is not None:
                    sample_info["blsampleid"]=blsampleid
                self.minidiffHO.simulateAutoCentring(sample_info=sample_info)
                res=self.continueCollect.Zzz(DataCollectPX2.CENTRESAMPLE_TIMEOUT)
                if res==CollectCondition.HARD_ABORT:
                    cancelAndContinue()
                    return (False,"sample centring aborted!")
                elif res==CollectCondition.SOFT_ABORT:
                    cancelAndContinue()
                    return (None,"sample centring aborted!")
                elif res==CollectCondition.PROCEED:
                    pass
                else:
                    if res==CollectCondition.TIMEOUT:
                        self.collectLog("timeout while waiting for sample centring!","error")
                        cancelAndContinue()
                    return (None,"unable to centre the sample!")
        else:
            try:
                centring_status=arguments["centring_status"]
            except:
                centring_status=None
            if centring_status is None and self.currentCentringStatus is not None:
                arguments["centring_status"]=copy.deepcopy(self.currentCentringStatus)

        return (True,)

    """
    prepareMacro4Collect
        Description: Sets the data collection parameters in spec using a spec channel; prepares the
                     self.persistentValues dictionary for the spec macro callbacks (ReplyArrived,
                     Ended, etc.); if the sample should be moved before the data collection sets
                     the centred_pos key (read inside spec).
        Type       : method
        Arguments  : arguments (dict; the collection parameters dictionary, based on the DNA XSD class 
                                Collect_request)
                     callback  (function; data collection callback, to be called just before the
                                collectFailed or collectEnded signals)
        Returns    : tuple ([0]=bool; result of the actions, True if OK, False if error
                            [1]=string; if [0]==False then it's the string error message, if [0]==True
                            then it does not exist!)
    """
    def prepareMacro4Collect(self,arguments,callback):
        # Adding loggin and print lines. Sync with PX1 (MS 13.09.2012) 
        logging.getLogger("HWR").debug('DataCollect:  prepareMacro4Collect ')
        #print     "prepareMacro4Collect: arguments= %s" %  arguments
        self.collectLog("preparing the macro...","debug")

        directory_snapshot=getArchiveDirectory(self.directoryPrefix(), directory=arguments['fileinfo']['directory'])
        if directory_snapshot is not None:
            arguments["archive_dir"]=directory_snapshot[0]
        else:
            arguments["archive_dir"]=""

        try:
            goto_centring_pos=arguments['centring_status']['goto']
        except:
            goto_centring_pos=False
        if goto_centring_pos:
            centring_pos_params=arguments['centring_status'].get('motors', {})
            arguments['centred_pos']=centring_pos_params
        
        #print "DataCollect.prepareMacro4Collect: arguments = %s" % arguments # Adding debugging line. Sync with PX1 (MS 13.09.2012)
        
        ### Here will follow code from PX1 that'll take care of energy, resolution, cryo ... (MS 13.09.2012)
        
        # PL. 31 Jan 2011
        # Apply energy requested from arg.
        #    The move is asynch, we have to wait.
        if "energy" in arguments and self.BLEnergyHO is not None:
            #print "888888 We need to change ENERGY !"
            try:
                target_energy = float(arguments["energy"])
                #print target_energy
                optimal_energy = self.BLEnergyHO.getEnergyComputedFromCurrentGap()
                print "%%%%%  OPT_E:",  optimal_energy
                abs_energy_diff = abs(target_energy-optimal_energy)
                print "%%%%%  ABS_E: ", abs_energy_diff
                if abs_energy_diff > 0.014:
                    stateI =  self.BLEnergyHO.BLEnergydevice.State
                    print "%%%%%  STATE0 BLE: ", stateI
                    self.BLEnergyHO.startMoveEnergy(target_energy)
                    time.sleep(0.1) # waiting for the start
                    debut = time.time()
                    while self.BLEnergyHO.BLEnergydevice.State != stateI:
                        #print "%%%%%  STATE1 BLE: ", stateI
                        duration = time.time() - debut
                        time.sleep(0.5)
                        print "Waiting for moving energy. t= %.3f sec" % duration
                        if duration > 10:
                            break
                #elif abs_energy_diff > 0.001:
                else:
                    print "%%%%%  STATE0 MONO: ", self.BLEnergyHO.monodevice.State
                    self.BLEnergyHO.monodevice.energy = target_energy
                    stateI = self.BLEnergyHO.monodevice.State
                    print "%%%%%  STATE1 MONO: ", stateI
                    time.sleep(0.1) # waiting for the start
                    debut = time.time()
                    while self.BLEnergyHO.monodevice.State != stateI:
                        print "%%%%%  STATE MONO: ", stateI
                        duration = time.time() - debut
                        print "Waiting for moving energy. t= %.3f sec" % duration
                        time.sleep(0.5)
                        if duration > 10:
                            break
            except:
                logging.getLogger("HWR").error("DataCollect.prepareMacro4Collect: can't change energy to %.3f keV" % target_energy)# 
        # PL. 13 Jan 2011
        # Apply resolution/distance requested from arg.
        # This needs to be done AFTER energy setup !
        #    The move is asynch, we have to wait.
        if "resolution" in arguments and self.resmotorHO is not None:
            try:
                target_resolution = float(arguments["resolution"]["upper"])
                print "^^^^0  RESOLUTION: ", self.resmotorHO.getState(), target_resolution, self.resmotorHO.getPosition()
                stateI = self.resmotorHO.getState()
                # PL_2011_06_10: Temporairement commente... avant modification. Moderation de la modification de la distance
                # si changement d'energy de faible amplitude... cf. 
                self.resmotorHO.move(target_resolution)
                time.sleep(0.5) # waiting for the start
                while self.resmotorHO.getState() != stateI:
                    time.sleep(0.05)
                    print "^^^^1  RESOLUTION: ", self.resmotorHO.getState(), target_resolution, self.resmotorHO.getPosition()
            except:
                logging.getLogger("HWR").error("DataCollect.prepareMacro4Collect: can't set resolution to %s" % target_resolution)
        # PL. 13 Jan 2011
        # Apply resolution/distance requested from arg.
        # This needs to be done AFTER energy setup !
        #    The move is asynch, we have to wait.         if "resolution" in arguments and self.resmotorHO is not None:
        if "transmission" in arguments and self.transmissionHO is not None:
            if True:
                target_transmission = float(arguments["transmission"])
                print "^^^^0  TRANSMISSION  state: %s   target:%.1f   current:%.1f" % \
                        (self.transmissionHO.getAttState(),
                        target_transmission, self.transmissionHO.getAttFactor())
                self.transmissionHO.setTransmission(target_transmission)
                time.sleep(0.2) # waiting for the start
        ### End of code from PX1 (MS 13.09.2012)
        
        # Commenting out the following snippet of code(comment + 5 lines), Sync with PX1 (MS 13.09.2012)
        ## Set parameters in spec (through a channel)
        #try:
            #self.argumentsChannel.setValue({})
            #self.argumentsChannel.setValue(arguments)
        #except Exception, diag:
            #return (False,"error setting arguments! (%s)" % str(diag))
        
        # Code analogical to the one on PX1, collectServer replaced by md2 on PX2 (MS 13.09.2012)
        #try:
            #md2device = DeviceProxy(self.getProperty('md2'))
        #except:
            #logging.getLogger("HWR").error("%s: unknown device name", self.getProperty('md2'))
        _state = self.md2device.State().name
        _status = self.md2device.Status()
        if _state not in  ["STANDBY", "OFF"]:
            return (False, "Not ready to start Collect. state= %s status= %s" % (_state, _status))
        
        
        #if centred_images is not None:
        #    arguments["centring_status"]["images"]=centred_images

        # Preserve some values needed when for the signals of the
        # macro ending/failing
        self.persistentValues["callback"]=callback
        self.persistentValues["stopped"]=False
        self.persistentValues["aborted"]=False
        self.persistentValues["macroStarted"]=False

        return (True,)

    """
    collect
        Description: Main API: starts a data collection. Receives all oscillation mandatory parameters (start
                     angle, overlap, etc.) beamline optional parameters (energy, transmission, etc.), optional
                     sample information (position in the sample changer, id of the ISPyB database, etc.) including
                     the centring status (centring accepted, snapshot images, centred motor positions, etc.).
        Algorithm  : 1. acquires the data collection lock
                     2. stores the parameters in self.persistentValues, required for the spec callbacks
                        of when the macro finishes
                     3. reads the sample info from the parameters
                     4. emits initial signals
                     5. reads the image info from the parameters and opens the log file
                     6. iterates through the individual collection phases: if some phase fails (i.e. returns
                        False) tries to rollback previous phases and returns the failure:
                        6.1 prepareParameters4Collect
                        6.2 prepareDatabase4Collect
                        6.3 prepareSampleChanger4Collect
                        6.4 prepareSample4Collect
                        6.5 prepareMacro4Collect
                        6.6 macroCollectCmd
                     7. the spec data collection macro starts
                     8. while the macro is executed, the only update is through a channel indicating the
                        image just exposed: image index, image filename, image intensity
                     9. eventually either the macro ends or fails; the final actions are similar: gather
                        the current beamline parameters from the result (energy, transmission, undulator
                        gaps, etc.), update the database and emit the resulting code.
                        
                     During the (simplified) actions described above, the data collection procedure can stop
                     several times while waiting for an external event. This includes waiting for the sample
                     changer to load a sample and waiting for the user (or automatic) centring to finish (or
                     give up...). This is done by blocking the current thread on the self.continueCollection
                     condition until some other thread tells it to continue (self.continueCollection.proceed()
                     in the sampleLoaded(self) callback, for example).
        Type       : method
        Arguments  : owner     (undefined type but should be a simple built-in python type like a string
                                or a number, not an instance; identifies who requested the data collection)
                     arguments (dict; the collection parameters dictionary, based on the DNA XSD class 
                                Collect_request)
                     callback  (function; data collection callback, to be called just before the
                                collectFailed or collectEnded signals)
        Returns    : tuple; [0]=collection state, True is OK and collecting, otherwise False or None; if
                            the state is not True, then [1] has an error message
        Threading  : Blocks the calling thread due to updating the database, mounting the sample and
                     waiting for the centring.
    """
    def collect(self,owner,arguments,callback=None):
        print "Debug MS 13.09.2012, about to start collection from within DataCollectPX2.collect()"
        # Adding logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  collect ')  
        # Cleanup the data collection and release resources
        def collectCleanup(msg,stat=False):
            self.collectLog(msg,"error")

            try:
                post_centring_running=self.threadRefs["postCentring"].aliveAndKicking()
            except (KeyError,AttributeError):
                post_centring_running=False
            if post_centring_running:
                self.threadRefs["postCentring"].respect()

            arguments["collection_code"]=stat
            arguments["collection_message"]=msg
            
            try:
                col_id=arguments["collection_datacollectionid"]
            except:
                col_id=None

            """ No idea what the last parameter (oscillation_id) is for since none of the bricks seem to use it """
            #self.guiEmit('collectOscillationFailed', (owner,stat,msg,col_id,col_id))
            self.guiEmit('collectOscillationFailed', (owner,stat,msg,col_id)) # Probably intended version of previous line. Sync with PX1 (MS 13.09.2012)
            if callback is not None:
                #callback((stat,msg),col_id)
                if isConsoleApplication():
                    callback((stat,msg),col_id)
                else:
                    self.collectEvent(callback,((stat,msg),col_id))
            self.guiEmit('collectFailed', (owner,stat,msg))

            self.persistentValues["owner"]=None
            self.persistentValues["callback"]=None
            self.persistentValues["arguments"]={}
            self.persistentValues["stopped"]=None
            self.persistentValues["aborted"]=None
            self.persistentValues["abortRequested"]=None
            self.persistentValues["macroStarted"]=None

            try:
                self.persistentValues["logFile"].close()
            except:
                pass
            self.persistentValues["logFile"]=None

            self.globalLock.release()
            self.collectLog("lock released(2)","debug")
            self.emitCollectReady()
            return (stat,msg)

        self.globalLock.acquire()
        self.collectLog("lock acquired(1)","debug")

        self.threadRefs={}

        if self.dbserverHO is not None and self.postImageThread is None:
            try:
                jpegserver=self.jpegserverHO
            except AttributeError:
                jpegserver=None
            self.postImageThread=startActionsThread(postImageActions(self.dbserverHO,jpegserver,self.directoryPrefix()))

        self.persistentValues["owner"]=owner
        self.persistentValues["abortRequested"]=None
        self.persistentValues["arguments"]=arguments
        try:
            self.persistentValues["arguments"]['centring_status'] = self.centring_status
        except AttributeError, diag:
            print diag
            #self.persistentValues["arguments"]
        #print "DataCollectPX2: collect, arguements", arguments

        try:
            blsampleid=int(arguments['sample_reference']['blSampleId'])
        except (KeyError,ValueError,TypeError):
            blsampleid=None

        sample_location=None
        sample_code=None
        try:
            sample_code=arguments['sample_reference']['code']
        except KeyError:
            pass
        else:
            if sample_code=="":
                sample_code=None
        try:
            basket_number=int(arguments['sample_reference']['container_reference'])
        except (KeyError,ValueError,TypeError):
            basket_number=None
        else:
            try:
                vial_number=int(arguments['sample_reference']['sample_location'])
            except (KeyError,ValueError,TypeError):
                vial_number=None
            else:
                sample_location=(basket_number,vial_number)
        if sample_location is None and sample_code is None and self.samplechangerHO is not None:
            sample_code=self.samplechangerHO.getLoadedSampleDataMatrix()
            #if sample_code is None:
            sample_location=self.samplechangerHO.getLoadedSampleLocation()

        arguments["collection_message"]="Starting a data collection..."

        self.cmdNotReady(force=True)
        print 'about to emit collectStarted signal'
        print 'owner', owner
        print 'number_of_images', arguments["oscillation_sequence"][0]['number_of_images']
        self.guiEmit('collectStarted', (owner, arguments["oscillation_sequence"][0]['number_of_images']))
        #self.guiEmit('collectOscillationStarted', (owner,blsampleid,sample_code,sample_location,arguments))

        if not self.configOk:
            return collectCleanup("DataCollect hardware object not properly configured!")

        # Open the log file
        directory=arguments['fileinfo']['directory']
        if not os.path.isdir(directory):
            logging.getLogger("HWR").info("Creating directory %s" % directory)
            try:
                makedirsRetry(directory)
            except OSError,diag:
                return collectCleanup("error creating directory %s! (%s)" % (directory,str(diag)))
        try:
            file_prefix=arguments['fileinfo']['prefix']
        except KeyError:
            file_prefix=""
        try:
            run_number=str(arguments['fileinfo']['run_number'])
        except KeyError:
            run_number="1"
        log_name="%s_%s.log" % (file_prefix,run_number)
        log_filename=os.path.join(directory,log_name)
        try:
            self.persistentValues["logFile"]=open(log_filename,"a")
        except:
            logging.getLogger("HWR").exception("Couldn't create the log file! (%s)" % log_filename)
            self.persistentValues["logFile"]=None
        self.collectLog("starting a data collection...")

        # Prepare the parameters (get some extra from spec, etc.)
        prep_params=self.prepareParameters4Collect(arguments)
        if not prep_params[0]:
            #self.undoSampleChanger(arguments)
            return collectCleanup(prep_params[1],prep_params[0])
        self.collectLog("parameters ok; going to next stage","debug")

        # Insert the collection into the database
        prep_db=self.prepareDatabase4Collect(arguments)
        if not prep_db[0]:
            #self.undoSampleChanger(arguments)
            return collectCleanup(prep_db[1])
        self.collectLog("database ok; going to next stage","debug")
        arguments["collection_datacollectionid"]=prep_db[1]
        self.currentDataCollectionId = prep_db[1] # This line is not present on PX1. Seems harmless though (MS 13.09.2012)

        # Load the correct sample
        prep_sc=self.prepareSampleChanger4Collect(arguments)
        if not prep_sc[0]:
            self.updateDatabase(prep_db[1],msg=prep_sc[1],images=0)
            return collectCleanup(prep_sc[1],prep_sc[0])
        self.collectLog("sample changer ok; going to next stage","debug")

        # Validate the centring
        prep_sample=self.prepareSample4Collect(prep_sc[1] is not None and not prep_sc[3],arguments)
        self.startPostCentringActions(arguments)
        if not prep_sample[0]:
            self.updateDatabase(prep_db[1],msg=prep_sample[1],images=0)
            self.undoSampleChanger(arguments)
            return collectCleanup(prep_sample[1],prep_sample[0])
        self.collectLog("sample ok; going to next stage","debug")

        # Store the collect parameters (required for when the macro ends/fails)
        prep_macro=self.prepareMacro4Collect(arguments,callback)
        
        # Adding code from PX1 (MS 13.09.2012)
        # PL. 31/01/2011 Add usefull information to the collect log.
        try:
            gap = self.BLEnergyHO.getCurrentUndulatorGap()
            wavelength = self.BLEnergyHO.getCurrentWavelength()
            self.updateDatabase(prep_db[1],
                                undu_gap0=gap,
                                wavelength=wavelength)
        except:
            pass
        try:
            distance = self.resmotorHO.device.position
            resolution = self.resmotorHO.dist2res(distance)
            self.updateDatabase(prep_db[1],
                                detdistance=distance,
                                resolution=resolution)
        except:
            pass 
        try:
            transmission = float(self.transmissionHO.getAttFactor())
            self.updateDatabase(prep_db[1], transmission=transmission)
        except:
            pass        
        # End of added PX1 code (MS 13.09.2012)
        
        if not prep_macro[0]:
            self.guiEmit('collectNumberOfFrames', (False, ))
            #self.updateDatabase(prep_db[1],msg=prep_macro[1],images=0) # commenting out. Sync with PX1 (MS 13.09.2012)
            #self.undoSampleChanger(arguments) # commenting out. Sync with PX1 (MS 13.09.2012)
            return collectCleanup(prep_macro[1])
        self.collectLog("macro ok; going to next stage","debug")
        
        # Finally call the collect macro
        time.sleep(0.5)

        try:
            print "here will go collect!"
            
            exposure = arguments['oscillation_sequence'][0]['exposure_time']
            start = arguments['oscillation_sequence'][0]['start']
            oscillation = arguments['oscillation_sequence'][0]['range']
            passes = arguments['oscillation_sequence'][0]['number_of_passes']
            nImages = arguments['oscillation_sequence'][0]['number_of_images']
            firstImage = arguments['oscillation_sequence'][0]['start_image_number']
            overlap = arguments['oscillation_sequence'][0]['overlap']
            reference_interval = arguments['oscillation_sequence'][0].get('reference_interval')
            
            print '\n'*10
            print 'reference_interval', reference_interval
            print '\n'*10
            prefix = arguments['fileinfo']['prefix']
            run = arguments['fileinfo']['run_number']
            suffix = arguments['fileinfo']['suffix']
            directory = arguments['fileinfo']['directory']
            template = arguments['fileinfo']['template']
            
            self.collectObject = Collect.collect(   
                                                    exposure = exposure,
                                                    oscillation = oscillation,
                                                    passes = passes,
                                                    start = start,
                                                    firstImage = firstImage,
                                                    nImages = nImages,
                                                    overlap = overlap,
                                                    directory = directory,
                                                    run = run,
                                                    prefix = prefix,
                                                    suffix = suffix,
                                                    template = template,
                                                    test = False,
                                                    inverse = reference_interval
                                                    #resolution = float(arguments["resolution"]["upper"]),
                                                    #energy = float(arguments["energy"])
                                                )
                   
            print 'self.collectObject', self.collectObject
            # MS 14.2.2013 trying to enable stop, abort and progress widgets
            self.guiEmit('collectOscillationStarted', (owner,blsampleid,sample_code,sample_location,arguments))
            
            self.collectObject.start()
            self.macroCollectStarted()
            #self.macroCollectEnded({'code': 2005, 'message': 'Hello, It is finished!'})
            
        except Exception, err:
            print err
            print Exception
            msg="problem calling collect sequence!"
            #self.guiEmit('collectSpecStarted', (False, ))
            #self.updateDatabase(prep_db[1],msg=msg,images=0)
            self.undoSampleChanger(arguments)
            return collectCleanup(msg)
        self.macroCollectEnded({'code': 2005, 'message': 'The collect is finished!'})
        return (True,)

    """
    sampleAcceptCentring
        Description: API to continue with the data collection while waiting for the sample to be
                     centred. Used if the centring is done by the user.
        Type       : method
        Arguments  : accepted        (bool; True if the centring was accepted, False if rejected)
                     centring_status (dict; the centring method, snapshots, etc.)
        Returns    : nothing
        Threading  : Wakes the thread blocked on the self.continueCollect condition object.
    """
    def sampleAcceptCentring(self, accepted, centring_status):
        print 'DataCollectPX2: sampleAcceptCentring, accepted' #, accepted
        self.centring_status = centring_status
        if not self.globalLock.locked():
            return
        if not self.waiting4UserCentring:
            return

        try:
            sample_id=int(self.persistentValues['arguments']['sample_reference']['blSampleId'])
        except (KeyError,ValueError,TypeError):
            sample_id=None

        self.persistentValues["arguments"]["centring_status"] = self.centring_status

        if accepted:
            self.collectLog("centring accepted")
            self.waiting4UserCentring=False
            self.continueCollect.proceed()
        else:
            self.collectLog("centring failed!")
            self.waiting4UserCentring=False
            self.continueCollect.failed()

    """
    minidiffAcceptCentring
        Description: Continues with the data collection while waiting for the sample to be
                     centred. Used if the centring was started by the DataCollect object
                     calling directly the Minidiff object.
        Type       : slot
        Arguments  : accepted (bool; True if the centring was accepted, False if rejected)
        Returns    : nothing
        Threading  : Wakes the thread blocked on the self.continueCollect condition object.
    """
    def minidiffCentringAccepted(self,accepted,centring_status):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  minidiffCentringAccepted ')
        self.centring_status = centring_status
        if not self.globalLock.locked():
            return
        if not self.waiting4AutoCentring:
            return

        self.persistentValues["arguments"]["centring_status"] = centring_status

        if accepted:
            self.collectLog("centring accepted")
            self.waiting4AutoCentring=False
            self.continueCollect.proceed()
        else:
            self.collectLog("centring failed!")
            self.waiting4AutoCentring=False
            self.continueCollect.failed()

    """
    startPostCentringActions
        Description: Starts the post-centring actions, like storing the current sample centred
                     positions and filename of the snapshots.
        Type       : method
        Arguments  : arguments (dict; the collection parameters dictionary, based on the DNA XSD class 
                                Collect_request)
        Returns    : nothing
        Threading  : Creates a new thread running postCentringActions.go()
    """
    def startPostCentringActions(self, arguments):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  startPostCentringActions ')
        postcentring_actions=postCentringActions(self)
        #try: # Remove reference to snapshots from the arguments
            ##arguments["centring_status"]["images"]=[]
        #except:
            #pass
        self.threadRefs["postCentring"]=startActionsThread(postcentring_actions)

    """
    sampleLoaded
        Description: Called when the sample changer successfully loads a sample
        Type       : callback
        Arguments  : already_loaded (bool; True if the sample was already loaded)
        Returns    : nothing
        Threading  : Wakes the thread blocked on the self.continueCollect condition object.
    """
    def sampleLoaded(self,already_loaded=False):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  sampleLoaded ')
        self.continueCollect.proceed()

    """
    loadSampleFailed
        Description: Called when the sample changer fails to load a sample
        Type       : callback
        Arguments  : state (string; indicates the sample changer state in result of the load action)
        Returns    : nothing
        Threading  : Wakes the thread blocked on the self.continueCollect condition object.
    """
    def loadSampleFailed(self,state):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  loadSampleFailed ')
        if state == 'FAULT':
            self.continueCollect.failed()
        elif state == 'ALARM':
            self.continueCollect.retry()
        else:
            self.continueCollect.failed()

    """
    undoSampleChanger
        Description: If the data collection arguments specified a sample to be loaded and the
                     parameter keep_sample_loaded is not set, then that sample is unloaded.
                     Tries 3 times to unload the sample.                     
        Type       : method
        Arguments  : arguments (dict; the collection parameters dictionary, based on the DNA XSD class 
                                Collect_request)
        Returns    : nothing
        Threading  : If unloading, blocks the calling thread on the self.continueCollect condition 
                     object.
        Signals    : collectUnmountingSample
    """
    def undoSampleChanger(self,arguments):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  undoSampleChanger ')
        try:
            keep_sample=str(arguments['keep_sample_loaded']).upper()=="TRUE"
        except (KeyError,TypeError,ValueError):
            keep_sample=False
        if keep_sample:
            return

        try:
            holder_length=arguments['sample_reference']['holderLength']
        except KeyError:
            holder_length=None

        try:
            sample_code=arguments['sample_reference']['code']
        except KeyError:
            sample_code=None
        else:
            if sample_code=="":
                sample_code=None

        sample_location=None
        #if sample_code is None:
        try:
            basket_number=int(arguments['sample_reference']['container_reference'])
        except (KeyError,ValueError,TypeError):
            basket_number=None
        else:
            try:
                vial_number=int(arguments['sample_reference']['sample_location'])
            except (KeyError,ValueError,TypeError):
                vial_number=None
            else:
                sample_location=(basket_number,vial_number)
        #sample_code=sample_location

        if sample_code is not None or sample_location is not None:
            if not self.samplechangerHO.sampleIsLoaded():
                self.collectLog("no mounted sample, skipping unmount","debug")
            else:
                self.guiEmit('collectUnmountingSample', (None,))
                self.collectLog("unmounting the sample")
                tries=DataCollectPX2.UNLOADSAMPLE_TRIES
                while tries>0:
                    self.continueCollect.reset()
                    self.collectEvent(self.samplechangerHO.unloadSample,(holder_length, None, None, self.sampleUnloaded, self.unloadSampleFailed))
                    self.collectLog("waiting for the sample to be unmounted...")
                    res=self.continueCollect.Zzz(DataCollectPX2.UNLOADSAMPLE_TIMEOUT)
                    if res==CollectCondition.RETRY:
                        tries-=1
                        if tries==0:
                            self.guiEmit('collectUnmountingSample', (False,))
                            self.collectLog("unable to unmount the sample!","error")
                        else:
                            self.collectLog("retrying to unmount the sample!","warning")
                    elif res==CollectCondition.PROCEED:
                        self.guiEmit('collectUnmountingSample', (True,))
                        tries=0
                    else:
                        if res==CollectCondition.TIMEOUT:
                            self.collectLog("timeout unmounting the sample!","error")
                        else:
                            self.collectLog("unable to unmount the sample!","error")
                        self.guiEmit('collectUnmountingSample', (False,))
                        tries=0
        else:
            pass

    """
    sanityCheck
        Description: Checks the data collection parameters (and DataCollect h.o. configuration) for
                     errors and warnings. Calls a spec macro and checks the state of the hutch interlock
                     (using the safety shutter).
        Type       : method
        Arguments  : arguments (dict; the collection parameters dictionary, based on the DNA XSD class 
                                Collect_request)
        Returns    : dict; "code"=True is nothing to worry about, False is errors, None if warnings;
                           "messages"=list of errors and warnings.
        Threading  : Blocks the calling thread (on the self.validCond condition object) until the
                     spec macro finishes.
    """
    def sanityCheck(self,arguments):
        val_code=True
        val_msg=[]
        centring_valid = False

        #if self.macroValidateParametersCmd is None:
            #logging.getLogger("HWR").warning("Undefined validate parameters spec macro!")
        #else:
            #if self.argumentsChannel is None:
                #val_code=None
                #val_msg.append("Invalid arguments spec channel!")
            #else:
                #for args in arguments:
                    #try:
                        #self.argumentsChannel.setValue({})
                        #self.argumentsChannel.setValue(args)
                    #except Exception,diag:
                        #logging.getLogger("HWR").error("Error setting arguments for validation (%s)" % str(diag))
                        #if val_code!=False:
                            #val_code=None
                        #val_msg.append("Error setting parameters for validation.")
                        #continue
                    #else:
                        #self.validLock.acquire()
                        #self.validCond.reset()
                        #self.macroValidateParametersCmd()
                        #res=self.validCond.Zzz(DataCollectPX2.SPEC_PARAMS_TIMEOUT)
                        #if type(res)!=types.DictType:
                            #try:
                                #self.macroValidateParametersCmd.abort()
                            #except:
                                #pass
                            #self.validLock.release()
                            #logging.getLogger("HWR").error("Error calling the validate parameters macro (unrecognized result: %s)" % str(res))
                            #if val_code!=False:
                                #val_code=None
                            #val_msg.append("Error calling the validate parameters spec macro.")
                            #continue

                        #self.validLock.release()
                        #try:
                            #spec_val_code=int(res['code'])
                        #except (KeyError,TypeError,ValueError):
                            #if val_code!=False:
                                #val_code=None
                            #val_msg.append("Error calling the validate parameters spec macro (no code key).")
                            #continue
                        #else:
                            #try:
                                #val_code={-1:False, 0:None, 1:True}[spec_val_code]
                            #except KeyError:
                                #if val_code!=False:
                                    #val_code=None
                                #val_msg.append("Error calling the validate parameters spec macro (unknown code key).")
                                #continue
                            #else:
                                #if not val_code:
                                    #try:
                                        #spec_msg=str(res['msg'])
                                    #except (KeyError):
                                        #if val_code!=False:
                                            #val_code=None
                                        #val_msg.append("Error calling the validate parameters spec macro (no msg key).")
                                        #continue
                                    #else:
                                        #spec_msg_ok=spec_msg.strip("\n").split("\n")
                                        #for msg_ok in spec_msg_ok:
                                            #msg_ok=msg_ok.strip()
                                            #if msg_ok[-1].isalpha() or msg_ok[-1].isdigit() or msg_ok[-1]==")":
                                                #msg_ok+="."
                                            #val_msg.append(msg_ok.capitalize())

        if not self.isSearchDone():
            val_msg.append("The hutch hasn't been searched!")
            if val_code!=False:
                val_code=None

        return {"code":val_code, "messages":val_msg}

    """
    getLastImageTakenBySpec
        Description: Reads the spec channel updated by spec when exposing an image.
        Type       : method
        Arguments  : none
        Returns    : int or None; the index number of the last image (i.e., the first image is always
                     1)
    """
    def getLastImageTakenBySpec(self):
        last_image=None
        try:
            image_info=self.imageCollectedChannel.getValue()
        except Exception,diag:
            self.collectLog("problem getting last image taken! (%s)" % str(diag),"warning")
        else:
            try:
                last_image=int(image_info.split()[0])
            except (ValueError,IndexError,TypeError),diag:
                self.collectLog("problem getting last image taken! (%s)" % str(diag),"warning")
            except AttributeError:
                try:
                    last_image=int(image_info['image_number'])
                except:
                    logging.getLogger("HWR").exception("Problem getting last image taken!")
                    self.collectLog("problem getting last image taken!",None)

        return last_image

    """
    processDataScripts
        Description    : executes a script after the data collection has finished
        Type           : method
    """
    def processDataScripts(self,processEvent): 
       try:
           server = self.autoProcessingServerProp
           if server is None:
               return
       except:
           return
       else:
           logging.getLogger().info("In processDataScripts...")

           processAnalyseParams = {}
           processAnalyseParams['EDNA_files_dir']=self.persistentValues["arguments"]["EDNA_files_dir"]

           try:
               processAnalyseParams['datacollect_id'] = self.persistentValues["arguments"]["collection_datacollectionid"] 
               processAnalyseParams['anomalous'] = self.persistentValues["arguments"]["anomalous"]
               processAnalyseParams['residues'] = self.persistentValues["arguments"]["residues"]
               processAnalyseParams['xds_dir'] = self.xds_dir
               processAnalyseParams['inverse_beam']=self.persistentValues["arguments"]["experiment_type"].endswith("Beam")
           except Exception,msg:
               logging.getLogger().exception("DataCollect:processing: %r" % msg)
           else:
               try:
                   server_proxy = xmlrpclib.Server("http://%s" % server)
               except:
                   logging.exception("Cannot create XML-RPC server instance")

               if str(self.persistentValues['arguments']['processing']) == 'True' and self.persistentValues['arguments'].get('input_files', False):
                 try: 
                     server_proxy.startProcessing(processEvent,processAnalyseParams)
                 except Exception,msg:
                     logging.getLogger().exception("Error starting processing, is the autoprocessing server correctly configured?: %r" % msg)
               if processEvent=="after" and str(self.persistentValues["arguments"]["do_inducedraddam"]) == 'True':
                 try:
                     #logging.info("executing: server_proxy.startInducedRadDam(%r)", processAnalyseParams)
                     server_proxy.startInducedRadDam(processAnalyseParams)
                 except Exception, msg:
                     logging.exception("Error starting induced rad.dam: %s", msg)
               
               """ Do not care what happens next """
   
 
    def updateDatabaseAfterCollect(self, msg, failed=False):
        floats = { "curr_wavelength": "self.lastWavelength",
                   "curr_distance": "self.lastDetDistPos",
                   "curr_resolution": "self.lastResPos",
                   "curr_transmission": "self.lastTransmission",
                   "resolutionAtCorner": "",
                   "undulatorGap0": "", "undulatorGap1": "", "undulatorGap2": "",
                   "beamSizeAtSampleX": "", "beamSizeAtSampleY":"",
                   "slitGapHorizontal": "", "slitGapVertical": "" }
        update_dict_keys = { "curr_wavelength": "wavelength",
                             "curr_distance": "detdistance",
                             "curr_resolution": "resolution",
                             "curr_transmission":"transmission",
                             "undulatorGap0": "undu_gap0", "undulatorGap1":"undu_gap1", "undulatorGap2":"undu_gap2",
                             "resolutionAtCorner":"resolution_at_corner",
                             "beamSizeAtSampleX": "beamSizeAtSampleX", "beamSizeAtSampleY": "beamSizeAtSampleY",
                             "slitGapHorizontal": "slitGapHorizontal", "slitGapVertical": "slitGapVertical" }
        update_dict = {}

        for key, attr in floats.iteritems():
          old_value = None
          if attr:
            try:
              old_value = eval(attr)
            except (NameError, AttributeError):
              pass
          try:
            value = float(self.lastMacroResult.get(key, old_value))
          except TypeError:
            logging.getLogger().warning("%s: updateDatabaseAfterCollect, parameter %s, type error: '%s' is not a float", self.name(), key, self.lastMacroResult.get(key, old_value))
            value = None           
          if key in update_dict_keys:
            update_dict[update_dict_keys[key]]=value
          if attr:
            exec attr+"="+str(value) 
 
        curr_beam_centre=None
        try:
            beam_centre_x=float(self.lastMacroResult['xbeam'])
        except:
            curr_beam_centre=self.calculateBeamCentre()
        else:
            try:
                beam_centre_y=float(self.lastMacroResult['ybeam'])
            except:
                curr_beam_centre=self.calculateBeamCentre()
            else:
                curr_beam_centre={'x':beam_centre_x,'y':beam_centre_y}
        update_dict["beam_centre"] = curr_beam_centre
        update_dict["beamShape"] = self.lastMacroResult.get("beamShape")
        update_dict["undu_type0"] = self.lastMacroResult.get("undulatorType0")
        update_dict["undu_type1"] = self.lastMacroResult.get("undulatorType1")
        update_dict["undu_type2"] = self.lastMacroResult.get("undulatorType2")        

        # Update the previous DB entry with successful/stopped status
        print "--->>>  persistentValues: a "#, 
        #pprint.pprint(self.persistentValues)
        
        #MS 19.09.2012. Adding try/except clause to handle not understood problem with missing 'collection_datacollectionid' KeyError
        try:
            update_dict["col_id"] = self.persistentValues["arguments"]["collection_datacollectionid"]
        except KeyError, e:
            update_dict["col_id"] = 1
            print "problem with 'collection_datacollectionid' key", e
            
        update_dict["images"] = None #number of images, in fact
        if failed or self.persistentValues["stopped"]:
            update_dict["images"]=self.undoMacro() 
        update_dict["msg"] = msg

        self.updateDatabase(**update_dict)
       
        return update_dict["col_id"]
 
    """
    updateDatabase
        Description: Updates the current data collection database entry. Accepts several optional
                     parameters: the None parameters are discarted while the others are written.
        Type       : method
        Arguments  : col_id               (int; the data collection id)
                     msg                  (string; the data collection status message)
                     images               (int; number of collected images)
                     wavelength           (float; wavelength during collection)
                     resolution           (float; resolution during collection)
                     detdistance          (float; detector distance during collection)
                     transmission         (float; transmission during collection)
                     beam_centre          (dict; "x"=beam centre horizontal pos; "y"=beam centre vertical pos
                     undu_gap0            (float; undulator 1 gap during collection)
                     undu_gap1            (float; undulator 2 gap during collection)
                     undu_gap2            (float; undulator 3 gap during collection)
                     resolution_at_corner (float; resolution at detector corner during collection)
                     snapshots            (list; 1 or 4 sample snapshot filenames)
                     centring_method      (string; sample centring method used)
        Returns    : nothing
        Threading  : Due to updating the database, the time to finish is unknown; might block the calling
                     thread while waiting for a HTTP timeout
    """
    def updateDatabase(self, col_id, **kwargs):
        mxcube2ispyb = { "msg": "runStatus",
                         "images": "numberOfImages",
                         "wavelength":"wavelength",
                         "resolution":"resolution",
                         "detdistance":"detectorDistance",
                         "transmission":"transmission",
                         "undu_gap0":"undulatorGap1", "undu_gap1":"undulatorGap2", "undu_gap2":"undulatorGap3",
                         "undu_type0":"undulatorType1", "undu_type1":"undulatorType2","undu_type2":"undulatorType3",
                         "resolution_at_corner":"resolutionAtCorner",
                         "centring_method":"centeringMethod",
                         "slitGapHorizontal": "slitGapHorizontal", "slitGapVertical": "slitGapVertical",
                         "beamSizeAtSampleX": "beamSizeAtSampleX", "beamSizeAtSampleY": "beamSizeAtSampleY",
                         "beamShape": "beamShape" }
        #logging.getLogger().info("updating database with %r", kwargs)
        
        #log_message = { "images": "images taken=%s",
        #                "wavelength": "wavelength=%s Ang",
        #                "resolution": "resolution=%s Ang",
        #                "detdistance": "detector distance=%s",
        #                "transmission": "transmission=%s%%",
        #               "undu_gap0": "undulator gap 1=%f",
        #                "undu_gap1": "undulator gap 2=%f",
        #                "undu_gap2": "undulator gap 2=%f",
        #                "undu_type0": "undulator type 1=%s",
        #                "undu_type1": "undulator type 2=%s",
        #                "undu_type2": "undulator type 3=%s",
        #                "resolution_at_corner": "resolution at corner=%s Ang",
        #                "centring_method": "centring method used=%s" }
        
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.persistentValues["arguments"]["collection_end_time"] = curr_time
        
        if col_id is None:
            return
        
        col_dict = { 'dataCollectionId': col_id, 'endTime': curr_time }

        for mxcube_arg, ispyb_arg in mxcube2ispyb.iteritems():
            value = kwargs.get(mxcube_arg)
            if value is not None:
                col_dict[ispyb_arg]=value
                #log_msg = log_message.get(mxcube_arg)
                #if log_msg:
                #    self.collectLog(log_msg % value, None)
        beam_centre = kwargs.get("beam_centre")
        if beam_centre:
            col_dict['xBeam'] = beam_centre['x']
            col_dict['yBeam'] = beam_centre['y']
            #self.collectLog("xbeam=%f" % beam_centre['x'],None)
            #self.collectLog("ybeam=%f" % beam_centre['y'],None)
        snapshots = kwargs.get("snapshots")
        if snapshots:
            try:
                col_dict['xtalSnapshotFullPath1']=snapshots[0]
            except:
                pass
            else:
                try:
                    col_dict['xtalSnapshotFullPath2']=snapshots[1]
                    col_dict['xtalSnapshotFullPath3']=snapshots[2]
                    col_dict['xtalSnapshotFullPath4']=snapshots[3]
                except:
                    pass
            
        #self.dbserverHO.updateDataCollection(col_dict) #Commenting for now MS 17.09.2012


    """
    undoMacro
        Description: Returns the number of images taken by spec during the last data collection
        Type       : method
        Arguments  : none
        Returns    : int; the number of images taken by spec
    """
    def undoMacro(self):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  undoMacro ')
        number_images=None
        last_image=self.getLastImageTakenBySpec()
        if last_image is not None:
            try:
                first_image=int(self.persistentValues["arguments"]["oscillation_sequence"][0]["start_image_number"])
            except (ValueError,TypeError):
                number_images=0
            else:
                number_images=last_image-first_image+1
        return number_images

    """
    stopCollect
        Description: Tries to stop the current data collection, either by setting a spec variable
                     through (this variable is monitored by the data collection macro) or by waking
                     up the thread blocked in self.continueCollect (waiting for a sample to be mounted
                     or centred) with the softAbort() method.
        Type       : method
        Arguments  : owner (string; not used)
        Returns    : tuple ([0]=stop state, True if stopping, False if nothing to stop; [1]=message)
        Threading  : Might wake up the thread blocked on the self.continueCollect condition
                     object.
    """
    def stopCollect(self,owner):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  stopCollect ')
        
        # Cleanup the stop request
        def stopCleanup(msg):
            self.collectLog(msg,"error")
            return (False,msg)
        
        # Added two debugging lines. Sync with PX1 (MS 13.09.2012)
        print "--->>>  persistentValues: x" #, 
        #pprint.pprint(self.persistentValues)
        print self.persistentValues
        self.persistentValues["stopped"] = True
        if self.persistentValues["owner"] is None:
            return stopCleanup("no collection to stop!")
        #if self.persistentValues["owner"]!=owner:
        #    return stopCleanup("DataCollect: cannot stop (invalid owner)")

        if not self.persistentValues["macroStarted"]:
            self.collectLog("trying to stop the current stage...")
            self.persistentValues["abortRequested"]=True
            self.continueCollect.softAbort()
            return (True,"Data collection will be stopped")
        
            print "--->>>  persistentValues: y" #, 
            #pprint.pprint(self.persistentValues)
        
        else:
            #if self.stopscanChannel is None:
                #return stopCleanup("cannot stop macro (invalid stopscan spec channel)!")

            self.collectLog("trying to stop the macro...")
            
            try:
                self.collectObject.stop()
                time.sleep(1)
                print 'limaadsc Status:', self.limaadscDevice.Status()
                print 'limaadsc State:', self.limaadscDevice.State()
                pprint.pprint(self.persistentValues)
                
            except Exception,diag:
                return stopCleanup("error stopping through the stopscan spec channel! (%s)" % str(diag))
            else:
               
                self.persistentValues["stopped"]=True
                
                self.macroCollectEnded('2005 Collect stopped')  # MS 19.09.2012
            return (True,"Data collection will be stopped after the current image")

    """
    macroValidateParametersEnded
        Description: Called when the parameters validation spec macro ends.
        Type       : slot
        Arguments  : result (dict; key "code" for the validation state: -1 for errors, 0 for warnings,
                             1 for OK; key "msg" for a string containing the messages separated by
                             \n).
        Returns    : nothing
        Threading  : Wakes the thread blocked on the self.validCond condition object.
    """
    def macroValidateParametersEnded(self,result):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  macroValidateParametersEnded ')
        if self.validLock.locked():
            self.validCond.proceedCustom(result)

    """
    macroValidateParametersFailed
        Description: Called when the parameters validation spec macro fails or is aborted.
        Type       : slot
        Arguments  : result (not used)
        Returns    : nothing
        Threading  : Wakes the thread blocked on the self.validCond condition object.
    """
    def macroValidateParametersFailed(self,result):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  macroValidateParametersFailed ')
        if self.validLock.locked():
            self.validCond.failed()

    """
    abortCollect
        Description: Tries to abort the current data collection, either by aborting the spec macro
                     or by waking up the thread blocked in self.continueCollect (waiting for a sample
                     to be mounted or centred) with the hardAbort() method.
        Type       : method
        Arguments  : owner (string; not used)
        Returns    : tuple ([0]=abort state, True if aborting, False if nothing to abort; [1]=message)
        Threading  : Might wake up the thread blocked on the self.continueCollect condition
                     object.
    """
    def abortCollect(self,owner):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  abortCollect ')
        #if self.persistentValues["owner"] is None:
            #return (False,"no collection to abort!")

        #self.macroCollectCmd.abort()
        self.persistentValues["aborted"] = True
        self.collectObject.abort()
        time.sleep(1)
        print 'limaadsc Status:', self.limaadscDevice.Status()
        print 'limaadsc State:', self.limaadscDevice.State()
        self.persistentValues["aborted"] = True
        #self.persistentValues["stopped"] = True
        self.macroCollectEnded('2005 Collect aborted')  # MS 20.09.2012
        return (True,"Data collection aborted")


    def xdsFileUpdate(self, xds_filename):
        xds_dir = os.path.dirname(xds_filename)
        if 'PROCESSED_DATA' in xds_dir:
          self.xds_dir = xds_dir

          # start before autoprocessing
          if 'processing' in self.persistentValues['arguments']:
            if self.persistentValues['arguments']['processing'] == 'True':
                self.processDataScripts('before')
 
    """
    messagesUpdate
        Description: Called when spec wants to display a message to the user, concerning the ongoing
                     data collection (basically it's a callback for a spec channel). Uses the "info"
                     level of the python logging module.
        Type       : slot
        Arguments  : string; the message to log and display
        Returns    : nothing
    """
    def messagesUpdate(self,msg):
        #if self.persistentValues['owner'] is None:
        #    return
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  messagesUpdate ')
        self.collectLog(msg)

    """
    imageCollectedUpdate
        Description: Called when spec exposes an image (basically it's a callback for a spec channel).
                     Emits a signal with the collected image index (the first image collected is always
                     1), the image filename and the measured image intensity.
        Type       : slot
        Arguments  : string or dict; expects either a string separated by spaces with the elements
                     image number (int; supposed to start with the start_image_number parameter),
                     image filename (string) and image intensity (float) or a dictionary with the
                     keys image_number, image_file, measuredIntensity.
        Returns    : nothing
        Signals    : collectImageTaken
    """
    def imageCollectedUpdate(self, current_image):
        logging.getLogger("HWR").debug('DataCollect: last image collected ' + current_image)
        
        #Commented out to check whether that was stopping us from having updates on images in progress bar MS 2013-06-26
        #if self.persistentValues['owner'] is None:
            #return

        # Get image information
        try:
            image_number, image_full_filename, image_intensity = current_image.split()
        except ValueError:
            self.collectLog("unknown update on a collected image! (%s)" % str(current_image),"warning")
            return
        except AttributeError:
            try:
                image_number=int(current_image['image_number'])
            except:
                return

            try:
                image_full_filename=current_image['image_file']
                image_intensity=current_image['measuredIntensity']
            except KeyError:
                self.collectLog("unknown update on a collected image! (%s)" % str(current_image),"warning")
                return

        try:
            im_intensity=float(image_intensity)
        except:
            self.lastImageIntensity=None
        else:
            self.lastImageIntensity=im_intensity

        self.collectLog("image %s: %s (intensity=%s)" % (image_number,image_full_filename,image_intensity))

        # Add the image to the queue
        try:
            col_id = self.persistentValues["arguments"]["collection_datacollectionid"]
        except (ValueError,TypeError):
            pass
        else:
            if self.postImageThread is not None:
                imageQueue.put((image_full_filename,col_id,image_intensity,\
                    self.lastMachineCurrent,self.lastMachineMessage,\
                    self.lastCryoTemperature))

        try:
            first_image=int(self.persistentValues["arguments"]["oscillation_sequence"][0]["start_image_number"])
            image_number=int(image_number)-first_image+1
            print 'imageCollectedUpdate'
            print 'self.guiEmit(\'collectImageTaken\', (image_number,))'
            print 'image_number', image_number
            print 'first_image', first_image
            #print '', 
            self.guiEmit('collectImageTaken', (image_number,))
        except (ValueError,TypeError), e:
            print 'Exception', e
            pass
        
        if self.persistentValues['arguments'].get('processing',False) == 'True' and self.persistentValues['arguments'].get('input_files', False):
            self.processDataScripts('image')

    """
    macroCollectStarted
        Description: Called when the data collection spec macro starts.
        Type       : slot
        Arguments  : none
        Returns    : nothing
        Signals    : collectNumberOfFrames
    """
    def macroCollectStarted(self):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  macroCollectStarted ')
        
        # Adapting for PX2 ... based on PX1
        self.persistentValues["macroStarted"]=True
        self.collectLog("starting data collection with md2")
        
        osc_seq = self.persistentValues["arguments"]["oscillation_sequence"][0]
        print "**** LEN of OSC_SEQ: ", len(self.persistentValues["arguments"]["oscillation_sequence"])
        
        #pprint.pprint(self.persistentValues["arguments"])
        fileinfo = self.persistentValues["arguments"]["fileinfo"]
        num_images = osc_seq["number_of_images"]
        start_num = osc_seq["start_image_number"]
        img_tmpl = os.path.join(fileinfo["directory"], fileinfo["template"])
        img_tmpl = img_tmpl.replace("####", "%04d")
        
        #self.guiEmit('collectSpecStarted', (True, self.collectObject.totalImages, ))
        self.guiEmit('collectNumberOfFrames', (True, self.collectObject.totalImages, ))
        
        
        # For ADXV visu (PL 26_07_2011; MS 2013-06-24).
        adxv_send_fmt = "\nload_image %s"#+ chr(32)
        try:
            adxv_sender = self.persistentValues["adxv"]
            if not adxv_sender:
                raise Exception
            # adxv_sender # test the connection ???
        except:
            try:
                self.connectVisualisation()
                time.sleep(1.)
                adxv_sender = self.persistentValues["adxv"]
            except:
                adxv_sender = None
                print "Warning: Can't connect to adxv for the following collect."
                
        while self.collectObject.state() == "STANDBY":
            time.sleep(0.1)
        
        lastImage = 0
        
        _coll_state = self.collectObject.state
        last_time_visu = 0
        _nerr = 0 
        
        def tryToLoad(currentImageName):
            currentImageName = os.path.join(self.collectObject.imagePath, currentImageName)
            try:
                print 'adxv_sender.send(adxv_send_fmt % currentImageName)'
                while not os.path.exists(currentImageName):
                    commands.getoutput('ls ' + self.collectObject.imagePath )
                    time.sleep(0.2)
                print 'command', adxv_send_fmt % currentImageName
                adxv_sender.send(adxv_send_fmt % currentImageName)
                adxv_sender.send('\n')
            except Exception, e:
                print e
        
        while self.collectObject.state() == "RUNNING":
            imageNum = self.collectObject.imageNum
            time.sleep(0.2)
            if lastImage < imageNum:
                currentImageName = self.collectObject.currentImageName
                intensity = str(self.collectObject.xbpm.intensity)
                
                if adxv_sender:
                    tryToLoad(currentImageName)
                
                if self.collectObject.totalImages >= imageNum > 0:
                    self.imageCollectedUpdate("%d %s %s" % (imageNum, currentImageName, intensity))
                lastImage = imageNum
        
        currentImageName = self.collectObject.currentImageName
        intensity = str(self.collectObject.xbpm.intensity)
        
        if adxv_sender:
            tryToLoad(currentImageName)
        
        self.imageCollectedUpdate("%d %s %s" % (imageNum, currentImageName, intensity))
        
        print "### DC:COLLECT: END2"
        #self.macroCollectEnded({'code': 2005, 'message': 'The collect is finished!'})
        

    """
    sampleUnloaded
        Description: Called when the sample changer successfully unloads a sample
        Type       : callback
        Arguments  : none
        Returns    : nothing
        Threading  : Wakes the thread blocked on the self.continueCollect condition object.
    """
    def sampleUnloaded(self):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  sampleUnloaded ')
        self.continueCollect.proceed()

    """
    unloadSampleFailed
        Description: Called when the sample changer fails to unload a sample
        Type       : callback
        Arguments  : state (string; indicates the sample changer state in result of the unload action)
        Returns    : nothing
        Threading  : Wakes the thread blocked on the self.continueCollect condition object.
    """
    def unloadSampleFailed(self, state):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  unloadSampleFailed ')
        if state == 'FAULT':
            self.continueCollect.failed()
        elif state == 'ALARM':
            self.continueCollect.retry()
        else:
            self.continueCollect.failed()

    """
    macroCollectEnded
        Description: Called when the data collection spec macro ends. If the macro result is not
                     understood or the result code is not 2005 (hardwired) then the macroCollectFailed
                     method is called instead. Since the database must be updated this method doesn't
                     do much: the majority of the actions are executed by a separate thread.
        Type       : slot
        Arguments  : result (string or dict; if string expects a number followed by a space followed
                             by a message; if dict expects a key named "code" with the collection code
                             - 2005 for success, -1 for fatal error, 0 for non-fatal error - and
                             "message" for the result message; also the following keys for the beamline
                             parameters: "curr_wavelength", "curr_distance", "curr_resolution",
                             "curr_transmission", "resolutionAtCorner", "xbeam", "ybeam", "undulatorGap0",
                             "undulatorGap1", "undulatorGap2")
        Returns    : nothing
        Threading  : Creates a new thread running macroEndedActions.go()
    """
    def macroCollectEnded(self,result):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  macroCollectEnded ')
        self.lastMacroResult={} #None
        if type(result)==types.DictType:
            self.lastMacroResult=result
            try:
                result_code=int(result['code'])
            except (KeyError,TypeError,ValueError):
                result_code=-1
            if result_code!=2005:
                try:
                    result_msg=result['message']
                except KeyError:
                    result_msg='default error message'
                if result_code==-1:
                    state=False
                else:
                    state=None
                self.macroCollectFailed(None,None,state,result_msg)
                return                
        else:
            try:
                result_list=str(result).split()
                result_code=int(result_list[0])
            except (TypeError,ValueError,IndexError,AttributeError),diag:
                self.macroCollectFailed(None,None,None,"didn't understand the result (please check spec)!")
                return

            if result_code!=2005:
                result_msg=""
                for el in result_list[1:]:
                    result_msg+=str(el)+" "
                result_msg=result_msg.strip()

                if result_code==-1:
                    state=False
                else:
                    state=None
                self.macroCollectFailed(None,None,state,result_msg)
                return

        self.processDataScripts("after")
        
        self.threadRefs["endedActions"]=startActionsThread(macroEndedActions(self))


    """
    macroCollectFailed
        Description: Called when the data collection spec macro fails. If the result from the macro
                     is not a dictionary then it tries to use the value of the fatalCollectChannel
                     spec variable. Since the database must be updated this method doesn't do much:
                     the majority of the actions are executed by a separate thread.
        Type       : slot (and eventually method, called by macroCollectEnded)
        Arguments  : result   (dict; expects a key named "code" with the collection code and "message"
                               for the result message; also the following keys for the beamline parameters:
                               "curr_wavelength", "curr_distance", "curr_resolution", "curr_transmission",
                               "resolutionAtCorner", "xbeam", "ybeam", "undulatorGap0", "undulatorGap1",
                               "undulatorGap2")
                     cmd_name (string; the name of the command, not used)
                     state    (bool; =False; forwarded to macroFailedActions)
                     message  (string; ="collection failed!"; forwarded to macroFailedActions)
        Returns    : nothing
        Threading  : Creates a new thread running macroFailedActions.go()
    """
    def macroCollectFailed(self,result,cmd_name,state=False,message="collection failed!"):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  macroCollectFailed ')
        self.lastMacroResult={} #None
        if type(result)==types.DictType:
            self.lastMacroResult=result
        elif self.fatalCollectChannel is not None:
            try:
                fatal_collect=self.fatalCollectChannel.getValue()
            except Exception,diag:
                self.collectLog("problem getting fatal collect return! (%s)" % str(diag),"warning")
            except:
                logging.getLogger("HWR").exception("Problem getting fatal collect return!")
                self.collectLog("problem getting fatal collect return!",None)
            else:
                try:
                    fatal_collect["message"]
                    fatal_collect["code"]
                except:
                    pass
                else:
                    self.lastMacroResult=fatal_collect

        try:
            macro_msg=str(self.lastMacroResult["message"])
        except:
            pass
        else:
            message=macro_msg

        if self.persistentValues["aborted"]:
            message="aborted by user's request!"

        try:
          self.collectCleanup()
        except:
          logging.getLogger("HWR").exception("%s: could not execute data collection cleanup", self.name())

        try:
            abortcleanup=self.abortcleanupcmdProp
        except AttributeError:
            abortcleanup=None
        if abortcleanup is not None and cmd_name is not None:
            self.collectLog("starting external cleanup command")
            try:
                subprocess.Popen(abortcleanup)
            except:
                self.collectLog("problem running external cleanup command!","warning")

        self.threadRefs["failedActions"]=startActionsThread(macroFailedActions(self,state,message))

    """
    macroCollectAborted
        Description: Called when the data collection spec macro is aborted (e.g.: ^C in spec)
        Type       : slot
        Arguments  : none
        Returns    : nothing
    """
    def macroCollectAborted(self):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  macroCollectAborted ')
        self.collectLog("data collection aborted!","warning")
        self.persistentValues["aborted"] = True
        # AJOUT PATRICK. Sync with PX1 (MS 13.09.2012)
        #self.persistentValues["stopped"] = True
        self.macroCollectEnded('2005 Collect aborted')

    """
    sampleChangerHO
        Description: Returns the sample changer h.o. defined in the data collect xml configuration
                     file
        Type       : method
        Arguments  : none
        Returns    : SampleChanger; the sample changer hardware object
    """
    def sampleChangerHO(self):
        return self.samplechangerHO

    """
    miniDiffHO
        Description: Returns the minidiff h.o. defined in the data collect xml configuration
                     file
        Type       : method
        Arguments  : none
        Returns    : MiniDiff; the minidiff hardware object
    """
    def miniDiffHO(self):
        return self.minidiffHO

    """
    dbServerHO
        Description: Returns the database client h.o. defined in the data collect xml configuration
                     file
        Type       : method
        Arguments  : none
        Returns    : ISPyBClient; the database client hardware object
    """
    def dbServerHO(self):
        return self.dbserverHO

    """
    directoryPrefix
        Description: Returns the data collection directory prefix defined in the data collect xml
                     configuration file
        Type       : method
        Arguments  : none
        Returns    : string; the prefix for all data collection directories
    """
    def directoryPrefix(self):
        return self.directoryprefixProp

    """
    customdirectoryPrefix
        Description: Returns the custom data collection directory prefix defined in the data collect xml
                     configuration file. This is used to configure a non-standard path to collect data into.
        Type       : method
        Arguments  : none
        Returns    : string; the prefix for all data collection directories
    """
    def customDirectoryPrefix(self):
        return self.customDirectoryPrefixProp


    """
    isInhouseUser
        Description: Checks if a proposal is inhouse (for example, the data collection directory
                     should be built with inhouse instead of external).
        Type       : method
        Arguments  : proposal_code   (string; the proposal code)
                     proposal_number (int; the proposal number)
        Returns    : bool; True if the proposal is an inhouse proposal, False otherwise
    """
    def isInhouseUser(self,proposal_code,proposal_number):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  isInhouseUser ')
        for inhouse_user in self.mxlocalParameters['inhouse_users']:
            if proposal_code==inhouse_user[0]:
                if inhouse_user[1] is None:
                    return True
                elif str(proposal_number)==str(inhouse_user[1]):
                    return True
        return False



"""
postImageActions
    Description: Performs the actions after collecting a detector image:
                 i)   gets the image details
                 ii)  inserts the image in the database by calling the database server
                 iii) converts the image to a jpeg by calling the jpeg server (deprecated!)
    Type       : class
    Arguments  : db_server        (instance; expects an ISPyBClient object)
                 jpeg_server      (instance; expects a JpegConnection object; deprecated!)
                 directory_prefix (string)
    API        : go()
    Threading  : Blocks the thread that calls the go() API on the global variable imageQueue
                 get() function
    Notes      : Meant to be used as a parameter for the startActionsThread function; the
                 go() functions has an infinite loop and never returns
"""
class postImageActions:
    def __init__(self,db_server,jpeg_server,directory_prefix):
        self.dbServer=db_server
        self.jpegServer=jpeg_server
        self.directoryPrefix=directory_prefix

    def go(self):
        logging.getLogger("HWR").debug("DataCollect: starting postImageActions thread")
        while True:
            image_info=imageQueue.get()

            info_filename=image_info[0]
            info_collection_id=image_info[1]
            try:
                info_intensity=float(image_info[2])
            except:
                info_intensity=None
            try:
                info_mach_current=image_info[3]
            except:
                info_mach_current=None
            info_mach_message=image_info[4]
            try:
                info_cryo_temp=image_info[5]
            except:
                info_cryo_temp=None

            # Store image in the database
            image_path,image_filename=os.path.split(info_filename)
            image_ext=os.path.splitext(image_filename)[1].strip()

            if info_collection_id is not None:
                logging.getLogger("HWR").debug("DataCollect: inserting %s into database" % info_filename)
                image_dict={'dataCollectionId':info_collection_id,\
                    'fileName':image_filename,\
                    'fileLocation':image_path,\
                    'measuredIntensity':info_intensity,\
                    'synchrotronCurrent':info_mach_current,\
                    'machineMessage':info_mach_message,\
                    'temperature':info_cryo_temp}
                directory_jpeg=getArchiveDirectory(self.directoryPrefix, directory=image_path)
                if directory_jpeg is not None:
                    jpeg_filename="%s.jpeg" % os.path.splitext(image_filename)[0]
                    thumb_filename="%s.thumb.jpeg" % os.path.splitext(image_filename)[0]
                    image_dict['jpegFileFullPath']=os.path.join(directory_jpeg[0],jpeg_filename)
                    image_dict['jpegThumbnailFileFullPath']=os.path.join(directory_jpeg[0],thumb_filename)
                self.dbServer.storeImage(image_dict)

            if self.jpegServer is not None:
                directory_jpeg=getArchiveDirectory(self.directoryPrefix, filename=info_filename)
                if directory_jpeg is not None:
                    target_dir,target_file=directory_jpeg
                    logging.getLogger("HWR").debug("DataCollect: converting %s to jpeg" % info_filename)
                    self.jpegServer.convert(info_filename,target_dir)



"""
macroEndedActions
    Description: Performs the actions if the spec macro finished (either the collection
                 was completed or it was stopped through the stop channel):
                 i)   stores the state, message in the arguments dictionary
                 ii)  gets the latest values for the wavelenght, detector distance, etc.
                 iii) updates the data collection entry in the database
                 iv)  unmounts the sample (only if it was loaded at the startup of the data
                      collection and the parameter keep_sample_loaded is False)
                 v)   Signals the end of the collection with collectOscillationFailed,
                      collectFailed, and calling the (optional) callback
                 vi)  closes the data collection log file and clears internal variables of
                      the DataCollect instance
                 vii) releases the DataCollect instance global lock and emits collectReady
    Type       : class
    Arguments  : data_collect (instance; expects a DataCollect object)
    Signals    : collectOscillationFailed, collectFailed, collectOscillationFinished,
                 collectEnded, collectReady (on the DataCollect instance)
    API        : go()
    Threading  : Due to updating the database, the time to finish the go() API is unknown;
                 might block the calling thread while waiting for a HTTP timeout
    Notes      : Meant to be used as a parameter for the startActionsThread function
"""
class macroEndedActions:
    # Leaving most of the code untouched, significant differences with PX1 for now (MS 13.09.2012)
    def __init__(self,data_collect):
        self.dataCollect=data_collect

    def go(self):
        # Added logging. Sync with PX1 (MS 13.09.2012)
        logging.getLogger("HWR").debug('DataCollect:  macroEndedActions ')
        msg="Collection successful"
        stat=True
        if self.dataCollect.persistentValues["stopped"]:
            msg="Collection stopped!"
            stat=None
            
        if self.dataCollect.persistentValues["aborted"]:
            msg="Collection aborted!"
            stat=None
        self.dataCollect.collectLog(msg)

        try:
            postcentring_running=self.dataCollect.threadRefs["postCentring"].aliveAndKicking()
        except (KeyError,AttributeError):
            postcentring_running=False
        if postcentring_running:
            self.dataCollect.collectLog("waiting for post-centring actions to finish...")
            self.dataCollect.threadRefs["postCentring"].respect()

        self.dataCollect.persistentValues["arguments"]["collection_code"]=stat
        self.dataCollect.persistentValues["arguments"]["collection_message"]=msg

        col_id = self.dataCollect.updateDatabaseAfterCollect(msg, failed=False)

        self.dataCollect.undoSampleChanger(self.dataCollect.persistentValues["arguments"])

        if self.dataCollect.persistentValues["stopped"]:
            self.dataCollect.collectLog("data collection stopped")
        elif self.dataCollect.persistentValues["aborted"]:
            self.dataCollect.collectLog("data collection aborted")
        else:
            self.dataCollect.collectLog("data collection successful")

        if self.dataCollect.persistentValues["stopped"] or self.dataCollect.persistentValues["aborted"]:
            self.dataCollect.guiEmit('collectOscillationFailed', (self.dataCollect.persistentValues["owner"],stat,msg,col_id))
            callback=self.dataCollect.persistentValues["callback"]
            if callback is not None:
                if isConsoleApplication():
                    callback((stat,msg),col_id)
                else:
                    self.dataCollect.collectEvent(callback,((stat,msg),col_id))
            self.dataCollect.guiEmit('collectFailed', (self.dataCollect.persistentValues["owner"],stat,msg))
        else:
            self.dataCollect.guiEmit('collectOscillationFinished', (self.dataCollect.persistentValues["owner"],stat,msg,col_id,0))
            callback=self.dataCollect.persistentValues["callback"]
            if callback is not None:
                if isConsoleApplication():
                    callback((stat,msg),col_id)
                else:
                    self.dataCollect.collectEvent(callback,((stat,msg),col_id))
            self.dataCollect.guiEmit('collectEnded', (self.dataCollect.persistentValues["owner"],stat,msg))

        self.dataCollect.persistentValues["owner"]=None
        self.dataCollect.persistentValues["callback"]=None
        self.dataCollect.persistentValues["arguments"]={}
        self.dataCollect.persistentValues["stopped"]=None
        self.dataCollect.persistentValues["aborted"]=None
        self.dataCollect.persistentValues["macroStarted"]=None
        try:        
            self.dataCollect.persistentValues["logFile"].close()
        except:
            pass
        self.dataCollect.persistentValues["logFile"]=None

        self.dataCollect.continueCollect.reset()

        self.dataCollect.persistentValues["abortRequested"]=None
        self.dataCollect.globalLock.release()
        self.dataCollect.collectLog("lock released(1)","debug")
        self.dataCollect.emitCollectReady()



"""
macroFailedActions
    Description: Performs the actions if the spec macro failed (or was explicitly aborted):
                 i)   stores the state, message in the arguments dictionary
                 ii)  gets the latest values for the wavelenght, detector distance, etc.
                 iii) updates the data collection entry in the database
                 iv)  unmounts the sample (only if it was loaded at the startup of the data
                      collection and the parameter keep_sample_loaded is False)
                 v)   Signals the end of the collection with collectOscillationFailed,
                      collectFailed, and calling the (optional) callback
                 vi)  closes the data collection log file and clears internal variables of
                      the DataCollect instance
                 vii) releases the DataCollect instance global lock and emits collectReady
    Type       : class
    Arguments  : data_collect (instance; expects a DataCollect object)
                 state        (bool)
                 message      (string)
    Signals    : collectOscillationFailed, collectFailed, collectReady (on the DataCollect
                 instance)
    API        : go()
    Threading  : Due to updating the database, the time to finish the go() API is unknown;
                 might block the calling thread while waiting for a HTTP timeout
    Notes      : Meant to be used as a parameter for the startActionsThread function
"""
class macroFailedActions:
    # Leaving the code untouched, significant differences with PX1 for now (MS 13.09.2012)
    def __init__(self,data_collect,state,message):
        self.dataCollect=data_collect
        self.state=state
        self.message=message

    def go(self):
        self.dataCollect.collectLog(self.message,"error")

        try:
            postcentring_running=self.dataCollect.threadRefs["postCentring"].aliveAndKicking()
        except (KeyError,AttributeError):
            postcentring_running=False
        if postcentring_running:
            self.dataCollect.collectLog("waiting for post-centring actions to finish...")
            self.dataCollect.threadRefs["postCentring"].respect()

        self.dataCollect.persistentValues["arguments"]["collection_code"]=self.state
        self.dataCollect.persistentValues["arguments"]["collection_message"]=self.message

        col_id = self.dataCollect.updateDatabaseAfterCollect(self.message, failed=True)

        self.dataCollect.undoSampleChanger(self.dataCollect.persistentValues["arguments"])

        self.dataCollect.collectLog("data collection failed")

        self.dataCollect.guiEmit('collectOscillationFailed', (self.dataCollect.persistentValues["owner"],self.state,self.message,col_id))
        callback=self.dataCollect.persistentValues["callback"]
        if callback is not None:
            if isConsoleApplication():
                callback((self.state,self.message),col_id)
            else:
                self.dataCollect.collectEvent(callback,((self.state,self.message),col_id))
        self.dataCollect.guiEmit('collectFailed', (self.dataCollect.persistentValues["owner"],self.state,self.message))

        self.dataCollect.persistentValues["owner"]=None
        self.dataCollect.persistentValues["callback"]=None
        self.dataCollect.persistentValues["arguments"]={}
        self.dataCollect.persistentValues["stopped"]=None
        self.dataCollect.persistentValues["aborted"]=None
        self.dataCollect.persistentValues["macroStarted"]=None
        try:
            self.dataCollect.persistentValues["logFile"].close()
        except:
            pass
        self.dataCollect.persistentValues["logFile"]=None

        self.dataCollect.continueCollect.reset()

        self.dataCollect.persistentValues["abortRequested"]=None
        self.dataCollect.globalLock.release()
        self.dataCollect.collectLog("lock released(3)","debug")
        self.dataCollect.emitCollectReady()



"""
postCentringActions
    Description: Performs the actions after the centring stage: storing or clearing
                 the sample centred motor positions in the BLSample table; stores the
                 centred snapshot images in the DataCollection table.
    Type       : class
    Arguments  : data_collect (instance; expects a DataCollect object)
    API        : go()
    Threading  : Due to updating the database, the time to finish the go() API is unknown;
                 might block the calling thread while waiting for a HTTP timeout
    Notes      : Meant to be used as a parameter for the startActionsThread function
"""
class postCentringActions:
    # Leaving the code untouched, significant differences with PX1 for now (MS 13.09.2012)
    
    def __init__(self, data_collect):
        print 'postCentringActions'
        self.dataCollect=data_collect
        # Reference the centred jpegs inside the thread
        self.centredImages=None
        try:
            centring_status=self.dataCollect.persistentValues['arguments']["centring_status"]
        except:
            pass
        else:
            try:
                self.centredImages=centring_status['images']
            except:
                self.centredImages=None

    def go(self):
        db_server=self.dataCollect.dbServerHO()
        
        try:
            sessionid=int(self.dataCollect.persistentValues['arguments']['sessionId'])
        except (ValueError,TypeError,KeyError,AttributeError):
            sessionid=None
        try:
            blsampleid=int(self.dataCollect.persistentValues['arguments']['sample_reference']['blSampleId'])
        except (KeyError,ValueError,TypeError,AttributeError):
            blsampleid=None
        try:
            datacollectionid=int(self.dataCollect.persistentValues['arguments']["collection_datacollectionid"])
        except (KeyError,ValueError,TypeError,AttributeError):
            datacollectionid=None

        try:
            #centring_status = self.centring_status
            #print 'DataCollectPX2: go, centring_status', centring_status
            centring_status=self.dataCollect.persistentValues['arguments']["centring_status"]
        except:
            centring_status={}
        try:
            centring_valid=centring_status["valid"]
        except:
            centring_valid=False
        try:
            centring_accepted=centring_status["accepted"]
        except:
            centring_accepted=False
        try:
            file_prefix=self.dataCollect.persistentValues['arguments']['fileinfo']['prefix']
        except KeyError:
            file_prefix=None
        try:
            run_number=str(self.dataCollect.persistentValues['arguments']['fileinfo']['run_number'])
        except KeyError:
            run_number=None
        try:
            directory=self.dataCollect.persistentValues['arguments']['fileinfo']['directory']
        except KeyError:
            directory=None

        blsample_dict={}
        # Store/clear centred position in the database
        if blsampleid is not None and db_server is not None:
            if centring_valid and sessionid is not None:
                try:
                    centred_motors=centring_status["motors"]
                except:
                    centred_motors={}
                try:
                    centred_extra_motors=centring_status["extraMotors"]
                except:
                    centred_extra_motors={}
                centred_pos_str="sessionId=%s" % sessionid
                for m in centred_motors:
                    centred_pos_str="%s %s=%f" % (centred_pos_str,m,centred_motors[m])
                for m in centred_extra_motors:
                    centred_pos_str="%s %s=%f" % (centred_pos_str,m,centred_extra_motors[m])

                blsample_dict['blSampleId']=blsampleid
                blsample_dict['lastKnownCenteringPosition']=centred_pos_str
                self.dataCollect.collectLog("Storing centred position  for sample %s" % blsampleid )

                db_server.updateBLSample(blsample_dict)
                logging.getLogger("HWR").debug("Motor positions saved:  %s " % centred_pos_str)

        # Save snapshots in the filesystem and update the database
        if centring_valid and centring_accepted and file_prefix is not None and run_number is not None and directory is not None:
            try:
                centring_method=centring_status["method"]
            except:
                centring_method=None

            centring_snapshots=None
            if self.centredImages is not None:
                directory_snapshot = getArchiveDirectory(self.dataCollect.directoryPrefix(), directory = directory)
                logging.getLogger("HWR").debug("Directory snapshot is %s" % directory_snapshot )
                self.dataCollect.collectLog("Directory snapshot is %s" % directory_snapshot )
                if directory_snapshot is not None:
                    directory_snapshot=directory_snapshot[0]
                    if not os.path.isdir(directory_snapshot):
                        try:
                            makedirsRetry(directory_snapshot)
                        except OSError, diag:
                            self.dataCollect.collectLog("error creating directory %s" % directory_snapshot,"error")
                            directory_snapshot=None

                    if directory_snapshot is not None:
                        snapshot_i=1
                        centring_snapshots=[]
                        for img in self.centredImages:
                            img_phi_pos=img[0]
                            img_data=img[1]
                            filename_snapshot="%s_%s_%s.snapshot.jpeg" % (file_prefix,run_number,snapshot_i)
                            full_snapshot=os.path.join(directory_snapshot,filename_snapshot)
                            try:
                                self.dataCollect.collectLog("saving snapshot %s (axis=%f)" % (full_snapshot,img_phi_pos),"info")
                                f = open(full_snapshot, "w")
                                f.write(img_data)
                            except:
                                logging.getLogger("HWR").exception("Could not save snapshot!")
                                self.dataCollect.collectLog("could not save snapshot",None)
                            try:
                                f.close()
                            except:
                                pass
                            centring_snapshots.append(full_snapshot)
                            snapshot_i+=1

            if datacollectionid is not None:
                self.dataCollect.updateDatabase(datacollectionid,snapshots=centring_snapshots,centring_method=centring_method)

        else:
            if not centring_valid:
                logging.getLogger("HWR").warning("DataCollect:go: centring not valid, snapshots not saved")
            if not centring_accepted:
                logging.getLogger("HWR").warning("DataCollect:go: centring not accepted, snapshots not saved")
            if not file_prefix:
                logging.getLogger("HWR").warning("DataCollect:go: file prefix is None, snapshots not saved")
            if not run_number:
                logging.getLogger("HWR").warning("DataCollect:go: run_number is None, snapshots not saved")
            if not run_number:
                logging.getLogger("HWR").warning("DataCollect:go: directory is None, snapshots not saved")

"""
CollectCondition
    Description: Base class for the ??Condition classes below; defines the possible range
                 of results
    Type       : class
    Notes      : Tries to emulate an abstract class by throwing an exception if an instance
                 is created
"""
class CollectCondition:
    (TIMEOUT, PROCEED, RETRY, FAILED, SOFT_ABORT, HARD_ABORT) = (0,1,2,3,4,5)
    def __init__(self):
        raise "NotImplemented"

"""
QtCondition
    Description: Synchronises 2 threads, where one waits for the other; features include
                 setting a timeout, saying to the stopped thread to retry, proceed, etc.
    Type       : class (CollectCondition)
    Arguments  : none
    API        : reset()
                 proceed()
                 retry()
                 failed()
                 softAbort()
                 hardAbort()
                 proceedCustom(result<?>)
                 <?> Zzz(timeout<int/None>)
"""
class QtCondition(CollectCondition):
    def __init__(self):
        self.condition=qt.QWaitCondition()
        self.mutex=qt.QMutex()
        self.result = None

    def reset(self):
        self.mutex.lock()
        self.result = None
        self.mutex.unlock()

    def proceed(self):
        self.mutex.lock()
        self.result = QtCondition.PROCEED
        self.condition.wakeOne()
        self.mutex.unlock()
        
    def retry(self):
        self.mutex.lock()
        self.result = QtCondition.RETRY
        self.condition.wakeOne()
        self.mutex.unlock()

    def failed(self):
        self.mutex.lock()
        self.result = QtCondition.FAILED
        self.condition.wakeOne()
        self.mutex.unlock()
        
    def softAbort(self):
        self.mutex.lock()
        self.result = QtCondition.SOFT_ABORT
        self.condition.wakeOne()
        self.mutex.unlock()

    def hardAbort(self):
        self.mutex.lock()
        self.result = QtCondition.HARD_ABORT
        self.condition.wakeOne()
        self.mutex.unlock()

    def proceedCustom(self,result):
        self.mutex.lock()
        self.result = result
        self.condition.wakeOne()
        self.mutex.unlock()

    def Zzz(self,timeout):
        self.mutex.lock()
        if self.result is None:
            if timeout is None:
                if not self.condition.wait(self.mutex):
                    self.result = QtCondition.TIMEOUT
            else:
                if not self.condition.wait(self.mutex,1000*timeout):
                    self.result = QtCondition.TIMEOUT
            
        self.mutex.unlock()
        return self.result

"""
PyCondition
    Description: Synchronises 2 threads, where one waits for the other; features include
                 setting a timeout, saying to the stopped thread to retry, proceed, etc.
    Type       : class (CollectCondition)
    Arguments  : none
    API        : reset()
                 proceed()
                 retry()
                 failed()
                 softAbort()
                 hardAbort()
                 proceedCustom(result<?>)
                 <?> Zzz(timeout<int/None>)
"""
class PyCondition(CollectCondition):
    def __init__(self):
        self.lock=threading.Lock()
        self.condition=threading.Condition(self.lock)
        self.result = None

    def reset(self):
        self.lock.acquire()
        self.result = None
        self.lock.release()

    def proceed(self):
        self.lock.acquire()
        self.result = PyCondition.PROCEED
        self.condition.notify()
        self.lock.release()
        
    def retry(self):
        self.lock.acquire()
        self.result = PyCondition.RETRY
        self.condition.notify()
        self.lock.release()

    def failed(self):
        self.lock.acquire()
        self.result = PyCondition.FAILED
        self.condition.notify()
        self.lock.release()

    def softAbort(self):
        self.lock.acquire()
        self.result = PyCondition.SOFT_ABORT
        self.condition.notify()
        self.lock.release()

    def hardAbort(self):
        self.lock.acquire()
        self.result = PyCondition.HARD_ABORT
        self.condition.notify()
        self.lock.release()

    def proceedCustom(self,result):
        self.lock.acquire()
        self.result = result
        self.condition.notify()
        self.lock.release()

    def Zzz(self,timeout):
        self.lock.acquire()
        if self.result is None:
            if timeout is None:
                self.condition.wait()
            else:
                self.condition.wait(timeout)
            if self.result is None:
                self.result = CollectCondition.TIMEOUT
        self.lock.release()
        return self.result



"""
QtThread
    Description: Common wrapper for the qt.QThread class; the thread just executes
                 the function go() of the given instance
    Type       : class (qt.QThread)
    Arguments  : go_obj (instance; must have go() API)
    API        : run()
                 <bool> aliveAndKicking()
                 respect()
"""
class QtThread(qt.QThread):
    def __init__(self,go_obj):
        qt.QThread.__init__(self)
        self.goObj=go_obj
    def run(self):
        self.goObj.go()
    def aliveAndKicking(self):
        return self.running()
    def respect(self):
        self.wait()
"""
PyThread
    Description: Common wrapper for the threading.Thread class; the thread just executes
                 the function go() of the given instance
    Type       : class (threading.Thread)
    Arguments  : go_obj (instance; must have go() API)
    API        : run()
                 <bool> aliveAndKicking()
                 respect()
"""
class PyThread(threading.Thread):
    def __init__(self,go_obj):
        threading.Thread.__init__(self)
        self.goObj=go_obj
    def run(self):
        self.goObj.go()
    def aliveAndKicking(self):
        return self.isAlive()
    def respect(self):
        self.join()



"""
QtLock
    Description: Common wrapper to control the access to a shared resource;
                 used by QtThread instances
    Type       : class (qt.QMutex)
    Arguments  : none
    API        : acquire()
                 release()
"""
class QtLock(qt.QMutex):
    def acquire(self):
        return self.lock()
    def release(self):
        return self.unlock()

"""
PyLock
    Description: Common wrapper to control the access to a shared resource;
                 used by PyThread instances
    Type       : class
    Arguments  : none
    API        : acquire(block<bool>=True)
                 release()
    Notes      : Since threading.Lock is a factory function instead of a class,
                 an internal lock is created in the instance (instead of using
                 inheritance)
"""
class PyLock:
    def __init__(self):
        self.myLock=threading.Lock()
    def locked(self):
        if self.myLock.acquire(False):
            self.myLock.release()
            return False
        return True
    def acquire(self,block=True):
        return self.myLock.acquire(block)
    def release(self):
        return self.myLock.release()



"""
startActionsThread
    Description: Creates a new thread that will execute the start() function of a given
                 instance. If it's a console application (if isConsoleApplication returns
                 True) uses PyThread/threading.Thread, otherwise uses QtThread/qt.QThread
    Type       : method
    Arguments  : actions_obj (instance; must have go() API)
    Returns    : A thread instance (either PyThread/threading.Thread or QtThread/qt.QThread)
    Threading  : Creates and starts a new thread
"""
def startActionsThread(actions_obj):
    if isConsoleApplication():
        t=PyThread(actions_obj)
    else:
        t=QtThread(actions_obj)
    if t is not None:
        t.start()
    return t



"""
getArchiveDirectory
    Description: Translates the data collection directory (or a detector image filename)
                 into the corresponding long-term archive directory (for the snapshots,
                 jpegs, DNA logs, etc.)
    Type       : method
    Arguments  : directory_prefix (string)
                 directory        (string)
                 filename         (string)
    Returns    : 
    Notes      : The directory and filename parameters cannot be used at the same time
                 (one of them must be None)
"""
def getArchiveDirectory(directory_prefix, directory=None, filename=None):
    #return '/927bis/ccd/2013/Run2/20130318/Commissioning/'
    res=None

    if directory is None and filename is None:
        logging.getLogger("HWR").debug("DataCollect: called getArchiveDirectory without any parameter!")
    elif directory is not None and filename is not None:
        logging.getLogger("HWR").debug("DataCollect: called getArchiveDirectory with both parameters!")
    elif directory is not None:
        if not directory_prefix in directory:
            logging.getLogger("HWR").warning("DataCollect:getArchiveDirectory called with directory path (%s) with no matching directory prefix for this beamline (%s)" % (directory, directory_prefix))
            return None

        dir_path_list=directory.split(os.path.sep)
        try:
            suffix_path=os.path.join(*dir_path_list[4:])
        except TypeError:
            return None
        else:
            if 'inhouse' in directory:
                archive_dir = os.path.join('/927bis/ccd', dir_path_list[2], suffix_path)
            else:
                archive_dir = os.path.join('/927bis/ccd',dir_path_list[3],dir_path_list[4],*dir_path_list[5:])
        if archive_dir[-1]!=os.path.sep:
            archive_dir+=os.path.sep
        res=(archive_dir,)
    else:
        image_directory,image_filename=os.path.split(filename)
        if not image_directory.startswith(directory_prefix):
            return None
        dir_path_list=image_directory.split(os.path.sep)
        try:
            suffix_path=os.path.join(*dir_path_list[4:])
        except TypeError:
            return None
        else:
            if 'inhouse' in directory:
                archive_dir = os.path.join('/927bis/ccd', dir_path_list[2], suffix_path)
            else:
                archive_dir = os.path.join('/927bis/ccd',dir_path_list[3],dir_path_list[4],*dir_path_list[5:])
        directory_path_list=archive_dir.split(os.path.sep)
        if archive_dir[-1]!=os.path.sep:
            archive_dir+=os.path.sep
        res=(archive_dir,os.path.join(archive_dir,image_filename))

    return res







"""
makedirsRetry
    Description: Creates a directory, retrying if an exception is thrown. Sleeps between tries.
                 Used to try to fix some network-mounted filesystem features...
    Type       : method
    Arguments  : directory (string)
    Returns    : nothing
    Threading  : Might cause the calling thread to sleep for a few seconds (between retries)
    Comments   : Uses os.makedirs to create the directory. Returns silently if the directory
                 already exists.
"""
def makedirsRetry(directory):
    retries=DataCollectPX2.MAKEDIRS_TRIES
    while retries>0:
        retries-=1
        try:
            os.makedirs(directory)
        except OSError,diag:
            if diag.errno==17:
                return
            if retries==0:
                raise
            logging.getLogger("HWR").debug("DataCollect: retrying to create directory %s (%s)" % (directory,str(diag)))
            time.sleep(DataCollectPX2.MAKEDIRS_TRY_SLEEP)
        else:
            return



"""
<procedure class="DataCollect">
  <!-- BEAMLINE DEPENDENT -->
  <specversion>host_template:spec_template</specversion>

   <!-- SHOULD NOT BE CHANGED UNLESS YOU KNOW WHAT YOU'RE DOING! -->
  <command type="spec" name="macroCollect">datacollection</command>
  <channel type="spec" name="arguments">datacollection_parameters</channel>
  <channel type="spec" name="imageCollected">CURRENT_IMAGE</channel>
  <command type="spec" name="macroValidateParameters">validate_collect_parameters</command>
  <channel type="spec" name="stopscan">STOP_COLLECT_LOOP</channel>
  <channel type="spec" name="messages">eprodc_log_message</channel>
  <channel type="spec" name="fatalCollect">eprodc_fatal_collect</channel>

  <!-- DEFAULT VALUES, SHOULD BE 99% CORRECT... -->
  <dbserver>/dbconnection</dbserver>
  <safetyshutter>/safshut</safetyshutter>
  <samplechanger>/sc</samplechanger>
  <minidiff>/minidiff</minidiff>
  <mxlocal>/mxlocal</mxlocal>
  <slitbox>/slitbox</slitbox>
  <machcurrent>/mach</machcurrent>
  <cryostream>/cryospy</cryostream>
  <energyscan>/energyscan</energyscan>
  <transmission>/attenuators</transmission>

  <!-- BEAMLINE DEPENDENT -->
  <detdistmotor>/eh?/DtoX</detdistmotor> 
  <resmotor>/eh?/res</resmotor>
  <directoryprefix>id??eh?</directoryprefix>

  <!-- DEPRECATED! -->
  <!--
  <jpegserver>/jpegconnection</jpegserver>
  <abortcleanupcmd>/users/blissadm/local/bin/start_detector</abortcleanupcmd>
  -->
</procedure>
"""
