# -*- coding: utf-8 -*-
"""
Wraps the DataCollect hardware object: instead of receiving just one dictionary
on the collect API (describing the oscillation parameters) it receives a list and
iterates through that list. Since each oscillation can have its own ISPyB database
blsampleid and sample changer barcode/location this hardware object provides a
multi-sample multi-oscillation data collection functionality.

The main changes are:
-the collect API now spawns a thread, never blocking the calling thread
-the collectOscillationStarted/Failed/Finished signal has an extra parameter: oscillation_id,
 to be used as arguments to getOscillation(oscillation_id<int>) to retrieve oscillations
-new skipOscillation(owner<string>) API to skip the ongoing oscillation and move to
 the next one in the list
-new getOscillation(oscillation_id<int>) to retrieve the arguments of a previous oscillation
-new getOscillation(oscillation_id<int>) to retrieve all oscillations per session

You can refer to the DataCollect h.o. file for more documentation on the methods,
written on their headers.


Main APIs
---------
collect(owner<string>,arguments<list>,callback<method>=None)
<dict> sanityCheck(arguments<dict>)
stopCollect(owner<string>)
abortCollect(owner<string>)
skipOscillation(owner<string>)
<tuple> getOscillation(oscillation_id<int>)
<list> getOscillations(session_id<int>)


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


Signals
-------
collectDisconnected()
collectConnected()
collectReady(state<bool>)
collectAxisMotorMoved(pos<float>)
collectStarted(owner<string>)
(*) collectOscillationStarted(owner<string>,blsampleid<int>,sample_code<string>,sample_location<tuple>,arguments<dict>,oscillation_id<int>)
collectMountingSample(sample_code<string>,sample_location<tuple>,mounted<bool/None>)
collectValidateCentring(sample_was_loaded<bool>,fileinfo<dict>)
collectRejectCentring()
collectNumberOfFrames(state<bool>,num_images<int/None>)
collectImageTaken(image_number<int>)
collectUnmountingSample(unmounted<bool/None>)
(*) collectOscillationFailed(owner<string>,stat<bool>,msg<string>,col_id<int>,oscillation_id<int>)
collectFailed(owner<string>,stat<bool>,msg<string>)
(*) collectOscillationFinished(owner<string>,stat<bool>,msg<string>,col_id<int>,oscillation_id<int>)
collectEnded(owner<string>,stat<bool>,msg<string>)

(*) = changed in relation to DataCollect, added an oscillation_id parameter to be used with getOscillation


(See the end of this file for an example of the XML configuration file.)
"""



### Modules ###
from HardwareRepository.BaseHardwareObjects import Procedure
from HardwareRepository import HardwareRepository
import logging
import DataCollectPX2



"""
MultiCollect
    Type: class
    (see DataCollect hardware object for details)
"""
class MultiCollectPX2(Procedure):
    def init(self):
        self.dataCollect=None
        self.currentCollection=None
        self.currentCollectionIndex=None
        self.currentOwner=None
        self.currentCallback=None
        self.currCollectThread=None
        self.oscillationHistory={}
        self.oscillationHistoryCounter=0
        self.oscillationPerSession={}
        self.isSkip=False
        data_collect=self.getProperty("datacollect")
        if data_collect is None:
            logging.getLogger("HWR").error('MultiCollect: you must specify the data collect hardware object')
        else:
            hobj=HardwareRepository.HardwareRepository().getHardwareObject(data_collect)
            print "Debug MS 13.09.2012, MultiCollectPX2 hobj", hobj
            if hobj is None:
                logging.getLogger("HWR").error('MultiCollect: invalid data collect hardware object')
            else:
                self.dataCollect=hobj

                self.connect(self.dataCollect,'collectReady', self.collectReady)
                self.connect(self.dataCollect,'collectStarted', self.collectStarted)
                self.connect(self.dataCollect,'collectNumberOfFrames', self.collectNumberOfFrames)
                self.connect(self.dataCollect,'collectImageTaken', self.collectImageTaken)
                self.connect(self.dataCollect,'collectEnded', self.collectEnded)
                self.connect(self.dataCollect,'collectFailed', self.collectFailed)
                self.connect(self.dataCollect,'collectValidateCentring', self.collectValidateCentring)
                self.connect(self.dataCollect,'collectRejectCentring', self.collectRejectCentring)
                self.connect(self.dataCollect,'collectConnected', self.collectConnected)
                self.connect(self.dataCollect,'collectDisconnected', self.collectDisconnected)
                self.connect(self.dataCollect,'collectOscillationStarted', self.collectOscillationStarted)
                self.connect(self.dataCollect,'collectOscillationFinished', self.collectOscillationFinished)
                self.connect(self.dataCollect,'collectOscillationFailed', self.collectOscillationFailed)
                self.connect(self.dataCollect,'collectMountingSample', self.collectMountingSample)
                self.connect(self.dataCollect,'collectUnmountingSample', self.collectUnmountingSample)
                self.connect(self.dataCollect,'collectAxisMotorMoved', self.collectAxisMotorMoved)

    def getCurrentEnergy(self):
        #Modif MS 14.09.2012, till energyscan is set up, try alternative way to get energy
        try:
            currentEnergy = self.dataCollect.energyscanHO.getCurrentEnergy()
            
        except AttributeError:
            #pass
            #currentEnergy = 12.65 #self.dataCollect.BLEnergyHO.Energy()  
            currentEnergy = self.dataCollect.BLEnergyHO.getCurrentEnergy()
        return currentEnergy
        
    def collect(self,owner,arguments,callback=None):
        self.isSkip=False

        if self.dataCollect is None:
            msg='MultiCollect: not properly configured'
            logging.getLogger("HWR").error(msg)
            return (False,msg)

        # Set the keep_sample_loaded key
        prev_sample_code=None
        prev_sample_basket=None
        prev_sample_vial=None
        prev_arg=None
        for arg in arguments:
            current_sample_code=None
            current_sample_basket=None
            current_sample_vial=None
            try:
                current_sample_code=arg['sample_reference']['code']
            except KeyError:
                try:
                    current_sample_basket=int(arg['sample_reference']['container_reference'])
                except (KeyError,ValueError,TypeError):
                    pass
                else:
                    try:
                        current_sample_vial=int(arg['sample_reference']['sample_location'])
                    except (KeyError,ValueError,TypeError):
                        current_sample_basket=None

            if prev_arg is not None:
                if prev_sample_code is not None and prev_sample_code==current_sample_code:
                    prev_arg["keep_sample_loaded"]=True
                elif prev_sample_basket is not None and prev_sample_basket==current_sample_basket and prev_sample_vial==current_sample_vial:
                    prev_arg["keep_sample_loaded"]=True

            prev_arg=arg
            prev_sample_code=current_sample_code
            prev_sample_basket=current_sample_basket
            prev_sample_vial=current_sample_vial

        self.currentCollection=arguments
        #print 'MS 2013-07-03 self.currentCollection', self.currentCollection
        self.currentCollectionIndex=0
        self.currentOwner=owner
        self.currentCallback=callback
        my_callback=None
        if self.currentCallback is not None:
            my_callback=self.collectCallback

        collect_dict=self.currentCollection[self.currentCollectionIndex]
        self.currCollectThread=DataCollectPX2.startActionsThread(CollectActions(self.dataCollect,self.currentOwner,collect_dict,my_callback))
        return (True,)

    def collectReady(self,state):
        last_oscillation=False
        if self.currentCollection is not None:
            try:
                self.currentCollection[self.currentCollectionIndex]
            except IndexError:
                last_oscillation=True
        if self.currentCollection is None or self.currentCollectionIndex==0 or last_oscillation:
            self.emit('collectReady', (state,))

    def collectAxisMotorMoved(self,pos):
        self.emit('collectAxisMotorMoved', (pos,))
        
    def collectStarted(self,owner):
        logging.getLogger("HWR").debug('MultiCollect: collect started for %s' % owner)
        if self.currentCollectionIndex==0:
            self.emit('collectStarted', (owner,len(self.currentCollection)))

    def collectNumberOfFrames(self,status,number_images=0):
        self.emit('collectNumberOfFrames', (status,number_images,))

    def collectImageTaken(self,image_number):
        self.emit('collectImageTaken', (image_number,))

    def collectOscillationStarted(self,owner,blsampleid,barcode,location,collect_dict):
        collect_dict=self.currentCollection[self.currentCollectionIndex]
        oscillation_id=self.oscillationHistoryCounter
        self.oscillationHistoryCounter+=1
        self.oscillationHistory[oscillation_id]=(blsampleid,barcode,location,collect_dict)
        try:
            sessionid=int(collect_dict["sessionId"])
        except:
            pass
        else:
            try:
                self.oscillationPerSession[sessionid].append(oscillation_id)
            except KeyError:
                self.oscillationPerSession[sessionid]=[oscillation_id]

        self.emit('collectOscillationStarted', (owner,blsampleid,barcode,location,collect_dict,oscillation_id))

    def collectOscillationFinished(self,owner,state,message,col_id):
        self.emit('collectOscillationFinished', (owner,state,message,col_id,self.oscillationHistoryCounter-1))

    def collectOscillationFailed(self,owner,state,message,col_id):
        self.emit('collectOscillationFailed', (owner,state,message,col_id,self.oscillationHistoryCounter-1))

    def collectEnded(self,owner,state,message):
        print "MS 17.09.2012. collectEnded"
        if self.isSkip:
            self.isSkip=False
        # Catching exception if self.currentCollectionIndex not int
        try:
            self.currentCollectionIndex += 1
        except TypeError:
            self.currentCollectionIndex = 1
        print 'MS 20.09.2012 debug, self.currentCollection', self.currentCollection
        try:
            collect_dict=self.currentCollection[self.currentCollectionIndex]
        except IndexError:
            self.multiCollectCleanup()
            self.emit('collectEnded', (owner,state,message))
        else:
            if self.currCollectThread is not None:
                self.currCollectThread.respect()
            my_callback=None
            if self.currentCallback is not None:
                my_callback=self.collectCallback
            self.currCollectThread=DataCollectPX2.startActionsThread(CollectActions(self.dataCollect,self.currentOwner,collect_dict,my_callback))

    def collectFailed(self,owner,state,message):
        if self.isSkip:
            self.collectEnded(owner,None,message)
        else:
            self.multiCollectCleanup()
            self.emit('collectFailed', (owner,state,message))

    def collectValidateCentring(self,sample_was_loaded,snapshot_fileinfo):
        self.emit('collectValidateCentring', (sample_was_loaded,snapshot_fileinfo))

    def collectRejectCentring(self):
        self.emit('collectRejectCentring', ())

    def collectMountingSample(self,barcode,location,stage):
        self.emit('collectMountingSample', (barcode,location,stage))

    def collectUnmountingSample(self,stage):
        self.emit('collectUnmountingSample', (stage,))

    def collectConnected(self):
        self.emit('collectConnected', ())

    def collectDisconnected(self):
        self.emit('collectDisconnected', ())

    def collectCallback(self,res,col_id=None):
        try:
            collect_dict=self.currentCollection[self.currentCollectionIndex+1]
        except IndexError:
            self.currentCallback(res,col_id)

    """
    multiCollectCleanup
        Description: Cleans up internal list and index to iterate through the oscillations to pass to
                     the DataCollect hardware object.
        Type       : method
        Arguments  : none
        Returns    : nothing
    """
    def multiCollectCleanup(self):
        self.currentCollection=None
        self.currentCollectionIndex=None
        self.currentOwner=None
        self.currentCallback=None

    def isConnected(self):
        return self.dataCollect.isConnected()

    def isReady(self):
        return self.dataCollect.isReady()

    def sampleChangerHO(self):
        return self.dataCollect.sampleChangerHO()

    def miniDiffHO(self):
        return self.dataCollect.miniDiffHO()

    def dbServerHO(self):
        return self.dataCollect.dbServerHO()

    def sanityCheck(self,collect_params):
        return self.dataCollect.sanityCheck(collect_params)

    def abortCollect(self,owner):
        return self.dataCollect.abortCollect(owner)

    def stopCollect(self,owner):
        return self.dataCollect.stopCollect(owner)

    """
    skipOscillation
        Description: Skips the current oscillation (i.e., one of the oscillation passed in the arguments
                     to the collect method).
        Type       : method
        Arguments  : owner (string)
        Returns    : nothing
    """
    def skipOscillation(self,owner):
        self.isSkip=True
        return self.dataCollect.stopCollect(owner)

    def setBrick(self,brick):
        if self.dataCollect is not None:
            return self.dataCollect.setBrick(brick)
        else:
            logging.getLogger("HWR").error('MultiCollect: no data collect hardware object to set interface brick')

    def getBeamlineConfiguration(self,keys):
        return self.dataCollect.getBeamlineConfiguration(keys)

    def calculateBeamCentre(self):
        return self.dataCollect.calculateBeamCentre()

    def getBeamlineCurrentParameters(self,keys):
        return self.dataCollect.getBeamlineCurrentParameters(keys)

    def directoryPrefix(self):
        return self.dataCollect.directoryPrefix()

    def isInhouseUser(self,proposal_code,proposal_number):
        return self.dataCollect.isInhouseUser(proposal_code,proposal_number)

    def getAxisPosition(self):
        return self.dataCollect.getAxisPosition()

    def collectEvent(self,method,arguments):
        return self.dataCollect.collectEvent(method,arguments)

    """
    getOscillation
        Description: Returns the arguments (and results) of an oscillation.
        Type       : method
        Arguments  : oscillation_id (int; the oscillation id, the last parameters of the collectOscillationStarted
                                     signal)
        Returns    : tuple; (blsampleid,barcode,location,arguments)
    """
    def getOscillation(self,oscillation_id):
        try:
            collect_dict=self.oscillationHistory[oscillation_id]
        except KeyError:
            collect_dict=None
        return collect_dict

    def clearOscillationHistory(self):
        for i in range(self.oscillationHistoryCounter):
            self.oscillationHistory.pop(i)
        self.oscillationPerSession={}

    def sampleAcceptCentring(self,accepted,centring_status):
        if not accepted:
            self.isSkip=True
        return self.dataCollect.sampleAcceptCentring(accepted,centring_status)

    def setCentringStatus(self,centring_status):
        return  self.dataCollect.setCentringStatus(centring_status)

    """
    getOscillations
        Description: Returns the history of oscillations for a session
        Type       : method
        Arguments  : session_id (int; the session id, stored in the "sessionId" key in each element
                                 of the arguments list in the collect method)
        Returns    : list; list of all oscillation_id for the specified session
    """
    def getOscillations(self,session_id):
        try:
            oscs=self.oscillationPerSession[int(session_id)]
        except:
            oscs=[]
        return oscs


"""
CollectActions
    Description: Starts a data collection (using the real data collection hardware object).
    Type       : class
    Arguments  : collect_obj (instance; expects a DataCollect object)
                 owner       (string)
                 params      (list)
                 callback    (python method)
    API        : go
    Threading  : Due to updating the database, the time to finish the go() API is unknown;
                 might block the calling thread while waiting for a HTTP timeout
    Notes      : Meant to be used as a parameter for the startActionsThread function
"""
class CollectActions:
    def __init__(self,collect_obj,owner,params,callback):
        self.collectObj = collect_obj
        self.owner = owner
        self.params = params
        self.callback = callback
    def go(self):
        print "Debug MS 13.09.2012, about to start collection from within MultiCollectPX2"
        self.collectObj.collect(self.owner,self.params,callback=self.callback)



"""
<procedure class="MultiCollect">
  <!-- DEFAULT VALUES, SHOULD BE 99% CORRECT... -->
  <datacollect>/datacollect</datacollect>
</procedure>
"""
