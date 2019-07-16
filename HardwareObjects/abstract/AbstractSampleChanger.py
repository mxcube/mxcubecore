#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
"""

--------------------------------------------
Description
--------------------------------------------

AbstractSampleChanger is a base class to help in the implementation of
Hardware Objects for SampleChangers following the
"SampleChanger Standard Interface".

If this class is used as base class a standard class is then provided for
its use by generic bricks or by MXCuBE itself.  This class exposes the
following API for bricks and MXCuBE:

--------------------------------------------
SampleChanger - Standard Interface
--------------------------------------------

Sample Changer States
----------------------

    SampleChangerState.Unknown
    SampleChangerState.Ready
    SampleChangerState.Loaded
    SampleChangerState.Loading
    SampleChangerState.Unloading
    SampleChangerState.Selecting
    SampleChangerState.Scanning
    SampleChangerState.Resetting
    SampleChangerState.Charging
    SampleChangerState.Moving
    SampleChangerState.ChangingMode
    SampleChangerState.StandBy
    SampleChangerState.Disabled
    SampleChangerState.Alarm
    SampleChangerState.Fault
    SampleChangerState.Initializing
    SampleChangerState.Closing

Commands
----------------------

load()
unload()
select()
abort()
changeMode()

getState()
getStatus()
isReady()
waitReady()
hasLoadedSample()
getLoadedSample()

Specifying sample locations
-----------------------------
The sample model in a sample changer is based
in the model:
   SampleChanger
      Container
         [Container...]
            Sample

Tipycally for a sample changer with Pucks and Sample
there is a single level for Container. Specifying
a sample location will consist in giving the puck (basket)
number followed by the sample number. In the location
example `3:5` the fifth sample in the third puck is specified.

For other more complex constructions (for example for
a plate manipulator) each nested container will be specified
until getting to the sample:

In the example for a location in a plate manipulator like `1:5:2`
the location specifies first plate well, fifth drop, second crystal.


Events emitted
----------------------

SampleChanger.STATE_CHANGED_EVENT
SampleChanger.STATUS_CHANGED_EVENT
SampleChanger.INFO_CHANGED_EVENT
SampleChanger.LOADED_SAMPLE_CHANGED_EVENT
SampleChanger.SELECTION_CHANGED_EVENT
SampleChanger.TASK_FINISHED_EVENT

Tools for SC Classes
----------------------

- useUpdateTimer (xml property):
   This property can accept a boolean value (True/False)

   If this property is set the HardwareObject will
   poll itself for state changes, information change and
   other needed values.

   Include a line like `<useUpdateTimer>True</useUpdateTimer`
   in the xml file



--------------------------------------------
How to implement derived SC Classes
--------------------------------------------

"""

import abc
import logging
import time
import gevent
import types


from HardwareRepository.TaskUtils import task
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.HardwareObjects.abstract.sample_changer.Container import Container, Sample


class SampleChangerState:
    """
    Enumeration of sample changer states
    """

    Unknown = 0
    Ready = 1
    Loaded = 2
    Loading = 3
    Unloading = 4
    Selecting = 5
    Scanning = 6
    Resetting = 7
    Charging = 8
    Moving = 9
    ChangingMode = 10
    StandBy = 11
    Disabled = 12
    Alarm = 13
    Fault = 14
    Initializing = 15
    Closing = 16

    STATE_DESC = {
        Ready: "Ready",
        Loaded: "Loaded",
        Alarm: "Alarm",
        Charging: "Charging",
        Disabled: "Disabled",
        Fault: "Fault",
        Loading: "Loading",
        Resetting: "Resetting",
        Scanning: "Scanning",
        Selecting: "Selecting",
        Unloading: "Unloading",
        Moving: "Moving",
        ChangingMode: "Changing Mode",
        StandBy: "StandBy",
        Initializing: "Initializing",
        Closing: "Closing",
    }

    @staticmethod
    def tostring(state):
        return SampleChangerState.STATE_DESC.get(state, "Unknown")


class SampleChangerMode:
    """
    Enumeration of sample changer operating modes
    """

    Unknown = 0
    Normal = 1
    Charging = 8
    Disabled = 11


class SampleChanger(Container, Equipment):
    """
    Abstract base class for sample changers
    """

    __metaclass__ = abc.ABCMeta

    # ########################    EVENTS    #########################
    STATE_CHANGED_EVENT = "stateChanged"
    STATUS_CHANGED_EVENT = "statusChanged"
    INFO_CHANGED_EVENT = "infoChanged"
    LOADED_SAMPLE_CHANGED_EVENT = "loadedSampleChanged"
    SELECTION_CHANGED_EVENT = "selectionChanged"
    TASK_FINISHED_EVENT = "taskFinished"
    CONTENTS_UPDATED_EVENT = "contentsUpdated"

    def __init__(self, type, scannable, *args, **kwargs):
        super(SampleChanger, self).__init__(type, None, type, scannable)
        if len(args) == 0:
            args = (type,)
        Equipment.__init__(self, *args, **kwargs)
        self.state = -1
        self.status = ""
        self._setState(SampleChangerState.Unknown)
        self.task = None
        self.task_proc = None
        self.task_error = None
        self._transient = False
        self._token = None
        self._timer_update_inverval = 5  # interval in periods of 100 ms
        self._timer_update_counter = 0

    def init(self):
        use_update_timer = self.getProperty("useUpdateTimer")

        if use_update_timer is None:
            use_update_timer = True

        logging.getLogger("HWR").info(
            "SampleChanger: Using update timer is %s " % use_update_timer
        )

        if use_update_timer:
            task1s = self.__timer_1s_task(wait=False)
            task1s.link(self._onTimer1sExit)
            updateTask = self.__update_timer_task(wait=False)
            updateTask.link(self._onTimerUpdateExit)

        self.use_update_timer = use_update_timer

        self.updateInfo()

    def _onTimer1sExit(self, task):
        logging.warning("Exiting Sample Changer 1s timer task")

    def _onTimerUpdateExit(self, task):
        logging.warning("Exiting Sample Changer update timer task")

    @task
    def __timer_1s_task(self, *args):
        while True:
            gevent.sleep(1.0)
            try:
                if self.isEnabled():
                    self._onTimer1s()
            except BaseException:
                pass

    @task
    def __update_timer_task(self, *args):
        while True:
            gevent.sleep(0.1)
            try:
                if self.isEnabled():
                    self._timer_update_counter += 1
                    if self._timer_update_counter >= self._timer_update_counter:
                        self._onTimerUpdate()
                        self._timer_update_counter = 0
            except BaseException:
                pass

    # ########################    TIMER    #########################
    def _setTimerUpdateInterval(self, value):
        self._timer_update_inverval = value

    def _onTimerUpdate(self):
        # if not self.isExecutingTask():
        self.updateInfo()

    def _onTimer1s(self):
        pass

    # #######################    EQUIPMENT    #######################

    def connectNotify(self, signal):
        logging.getLogger().info("connectNotify " + str(signal))

    # ########################    PUBLIC    #########################

    def getState(self):
        """
        Returns sample changer state
        :rtype: SampleChangerState
        """
        return self.state

    def getStatus(self):
        """
        Returns textual description of state
        :rtype: str
        """
        return self.status

    def getTaskError(self):
        """
        Description of the error of last executed task (or None if success).
        :rtype: str
        """
        return self.task_error

    def isReady(self):
        """
        Description of the error of last executed task (or None if success).
        :rtype: str
        """
        return (
            self.state == SampleChangerState.Ready
            or self.state == SampleChangerState.Loaded
            or self.state == SampleChangerState.Charging
            or self.state == SampleChangerState.StandBy
        )

    def waitReady(self, timeout=-1):
        start = time.clock()
        while not self.isReady():
            if timeout > 0:
                if (time.clock() - start) > timeout:
                    raise Exception("Timeout waiting ready")
            gevent.sleep(0.01)

    def isNormalState(self):
        """
        Description of the error of last executed task (or None if success).
        :rtype: str
        """
        return (
            self.state != SampleChangerState.Disabled
            and self.state != SampleChangerState.Alarm
            and self.state != SampleChangerState.Fault
            and self.state != SampleChangerState.Unknown
        )

    def isEnabled(self):
        return self.state != SampleChangerState.Disabled

    def assertEnabled(self):
        if not self.isEnabled():
            raise Exception("Sample Changer is disabled")

    def assertNotCharging(self):
        if self.state == SampleChangerState.Charging:
            raise Exception("Sample Changer is in Charging mode")

    def assertCanExecuteTask(self):
        if not self.isReady():
            raise Exception(
                "Cannot execute task: bad state ("
                + SampleChangerState.tostring(self.state)
                + ")"
            )

    def isTaskFinished(self):
        """
        Description of the error of last executed task (or None if success).
        :rtype: str
        """
        return self.isReady() or (
            (not self.isNormalState()) and (self.state != SampleChangerState.Unknown)
        )

    def isExecutingTask(self):
        """
        Description of the error of last executed task (or None if success).
        :rtype: str
        """
        return self.task is not None

    def waitTaskFinished(self, timeout=-1):
        start = time.clock()
        while not self.isTaskFinished():
            if timeout > 0:
                if (time.clock() - start) > timeout:
                    raise Exception("Timeout waiting end of task")
            gevent.sleep(0.01)

    def getLoadedSample(self):
        """
        Returns current loaded sample
        :rtype: str
        """
        for s in self.getSampleList():
            if s.isLoaded():
                return s
        return None

    def hasLoadedSample(self):
        """
        Returns current loaded sample
        :rtype: str
        """
        return self.getLoadedSample() is not None

    def is_mounted_sample(self, sample_location):
        try:
            return self.getLoadedSample().getCoords() == sample_location
        except AttributeError:
            return False

    def abort(self):
        """
        Aborts current task and puts device in safe state
        """
        self._doAbort()
        if self.task_proc is not None:
            self.task_proc.join(1.0)
            if self.task_proc is not None:
                self.task_proc.kill(Exception("Task aborted"))
                self.task = None
                self.task_proc = None
                self.task_error = None

    def updateInfo(self):
        """
        """
        former_loaded = self.getLoadedSample()
        self._doUpdateInfo()
        if self._isDirty():
            self._triggerInfoChangedEvent()

        loaded = self.getLoadedSample()
        if loaded != former_loaded:
            if (
                (loaded is None)
                or (former_loaded is None)
                or (loaded.getAddress() != former_loaded.getAddress())
            ):
                self._triggerLoadedSampleChangedEvent(loaded)

        self._resetDirty()

    def isTransient(self):
        return self._transient

    def _setTransient(self, value):
        self._transient = value

    def getToken(self):
        return self._token

    def setToken(self, token):
        self._token = token

    def getSampleProperties(self):
        return ()

    # ########################    TASKS    #########################
    def changeMode(self, mode, wait=True):
        """
        Change the mode (SC specific, imply change of the State)
        Modes:
            Unknown     = 0
            Normal      = 1
            Charging    = 2
            Disabled    = 3
        """
        if mode == SampleChangerMode.Unknown:
            return
        elif mode == self.getState():
            return
        if self.getState() == SampleChangerState.Disabled:
            self._setState(SampleChangerState.Unknown)
            self.updateInfo()
        elif mode == SampleChangerMode.Disabled:
            self._setState(SampleChangerState.Disabled)
        return self._executeTask(
            SampleChangerState.ChangingMode, wait, self._doChangeMode, mode
        )

    @task
    def scan(self, component=None, recursive=False):
        if isinstance(component, types.ListType):
            for c in component:
                self._scan_one(c, recursive)
        else:
            return self._scan_one(component, recursive)

    def _scan_one(self, component, recursive):
        self.assertNotCharging()
        if component is None:
            component = self
        component = self._resolveComponent(component)
        component.assertIsScannable()
        return self._executeTask(
            SampleChangerState.Scanning, True, self._doScan, component, recursive
        )

    def select(self, component, wait=True):
        component = self._resolveComponent(component)
        ret = self._executeTask(
            SampleChangerState.Selecting, wait, self._doSelect, component
        )
        self._triggerSelectionChangedEvent()
        return ret

    def chained_load(self, sample_to_unload, sample_to_load):
        self.unload(sample_to_unload)
        self.waitReady(timeout=10)
        return self.load(sample_to_load)

    def load(self, sample=None, wait=True):
        """
        Load a sample.
        """
        sample = self._resolveComponent(sample)
        self.assertNotCharging()
        # Do a chained load in this case
        if self.hasLoadedSample():
            # Do a chained load in this case
            if (sample is None) or (sample == self.getLoadedSample()):
                raise Exception(
                    "The sample "
                    + str(self.getLoadedSample().getAddress())
                    + " is already loaded"
                )
            return self.chained_load(self.getLoadedSample(), sample)
        else:
            return self._executeTask(
                SampleChangerState.Loading, wait, self._doLoad, sample
            )

    def unload(self, sample_slot=None, wait=True):
        """
        Unload the sample.
        If sample_slot=None, unloads to the same slot it was loaded from.
        """
        sample_slot = self._resolveComponent(sample_slot)
        self.assertNotCharging()
        # In case we have manually mounted we can command an unmount
        if not self.hasLoadedSample():
            raise Exception("No sample is loaded")
        return self._executeTask(
            SampleChangerState.Unloading, wait, self._doUnload, sample_slot
        )

    def reset(self, wait=True):
        """
        Reset the SC.
        If sample_slot=None, unloads to the same slot it was loaded from.
        """
        return self._executeTask(SampleChangerState.Resetting, wait, self._doReset)

    def _load(self, sample=None):
        self._doLoad(sample)

    def _unload(self, sample_slot=None):
        self._doUnload(sample_slot)

    def _resolveComponent(self, component):
        if component is not None and isinstance(component, basestring):
            c = self.getComponentByAddress(component)
            if c is None:
                raise Exception("Invalid component: " + component)
            return c
        return component

    # ########################    ABSTRACTS    #########################

    @abc.abstractmethod
    def _doAbort(self):
        """
        Aborts current task and puts device in safe state
        """
        return

    @abc.abstractmethod
    def _doUpdateInfo(self):
        return

    @abc.abstractmethod
    def _doChangeMode(self, mode):
        return

    @abc.abstractmethod
    def _doScan(self, component, recursive):
        return

    @abc.abstractmethod
    def _doSelect(self, component):
        return

    @abc.abstractmethod
    def _doLoad(self, sample):
        return

    @abc.abstractmethod
    def _doUnload(self, sample_slot=None):
        return

    @abc.abstractmethod
    def _doReset(self):
        return

    # ########################    PROTECTED    #########################

    def _executeTask(self, task, wait, method, *args):
        self.assertCanExecuteTask()
        logging.debug("Start " + SampleChangerState.tostring(task))
        self.task = task
        self.task_error = None
        self._setState(task)
        ret = self._run(task, method, wait=False, *args)
        self.task_proc = ret

        ret.link(self._onTaskEnded)
        if wait:
            return ret.get()
        else:
            return ret

    @task
    def _run(self, task, method, *args):
        """
        method(self,*arguments)
        exeption=None
        try:
            while !_isTaskFinished(state):
              time.sleep(0.1)
            exeption=_getTaskException(state)
        finally:
            _triggerTaskFinishedEvent(state,exeption)
            self._setState(SampleChangerState.Ready)
        """
        exception = None
        ret = None
        try:
            ret = method(*args)
        except Exception as ex:
            exception = ex
        # if self.getState()==self.task:
        #    self._setState(SampleChangerState.Ready)
        self.updateInfo()
        task = self.task
        self.task = None
        self.task_proc = None
        self._triggerTaskFinishedEvent(task, ret, exception)
        if exception is not None:
            self._onTaskFailed(task, exception)
            raise exception
        return ret

    def _onTaskFailed(self, task, exception):
        pass

    def _onTaskEnded(self, task):
        try:
            e = task.get()
            logging.debug("Task ended. Return value: " + str(e))
        except Exception as errmsg:
            logging.error("Error while executing sample changer task: %s", str(errmsg))

    def _setState(self, state=None, status=None):
        if (state is not None) and (self.state != state):
            former = self.state
            self.state = state
            if status is None:
                status = SampleChangerState.tostring(state)
            self._triggerStateChangedEvent(former)

        if (status is not None) and (self.status != status):
            self.status = status
            self._triggerStatusChangedEvent()

    def _resetLoadedSample(self):
        for s in self.getSampleList():
            s._setLoaded(False)
        self._triggerLoadedSampleChangedEvent(None)

    def _setLoadedSample(self, sample):
        for s in self.getSampleList():
            if s != sample:
                s._setLoaded(False)
            else:
                s._setLoaded(True)
        self._triggerLoadedSampleChangedEvent(sample)

    def _setSelectedSample(self, sample):
        cur = self.getSelectedSample()
        if cur != sample:
            Container._setSelectedSample(self, sample)
            self._triggerSelectionChangedEvent()

    def _setSelectedComponent(self, component):
        cur = self.getSelectedComponent()
        if cur != component:
            Container._setSelectedComponent(self, component)
            self._triggerSelectionChangedEvent()

    # ########################    PRIVATE    #########################

    def _triggerStateChangedEvent(self, former):
        self.emit(self.STATE_CHANGED_EVENT, (self.state, former))

    def _triggerStatusChangedEvent(self):
        self.emit(self.STATUS_CHANGED_EVENT, (str(self.status),))

    def _triggerLoadedSampleChangedEvent(self, sample):
        self.emit(self.LOADED_SAMPLE_CHANGED_EVENT, (sample,))

    def _triggerSelectionChangedEvent(self):
        self.emit(self.SELECTION_CHANGED_EVENT, ())

    def _triggerInfoChangedEvent(self):
        self.emit(self.INFO_CHANGED_EVENT, ())

    def _triggerTaskFinishedEvent(self, task, ret, exception):
        self.emit(self.TASK_FINISHED_EVENT, (task, ret, exception))

    def _triggerContentsUpdatedEvent(self):
        self.emit(self.CONTENTS_UPDATED_EVENT)
