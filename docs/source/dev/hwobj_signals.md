# MXCuBECore HardwareObject signals

:Created: 20240318

MXCuBE relies heavily on signals being emitted and listened to by many elements. For example, a hardware object may listen to other lower level hardware objects in order to update values after some calculation. But it is also critical in the UI (both web and Qt), in both cases they expect periodic signal updates for displaying the most recent information to the user (e.g. motor positions, data collection state, etc.)

## Implementation

Depending on the installed modules, signals are emitted using [Louie](https://pypi.org/project/Louie/) or [PyDispatcher](https://pypi.org/project/PyDispatcher/). The former being based on the later. The developer does not need to deal with the differences between those two modules as it is already being handled in the file [dispatcher](https://github.com/mxcube/mxcubecore/blob/develop/mxcubecore/dispatcher.py).
 **_NOTE:_**  can we remove any of those dependencies?


> PyDispatcher provides the Python programmer with a multiple-producer-multiple-consumer signal registration and routing infrastructure for use in multiple contexts


When certain events or conditions occur within a hardware object, corresponding signals are emitted to inform connected components or modules about these changes.

The {py:class}`mxcubecore.BaseHardwareObjects.HardwareObject` class serves as the base class for all hardware objects in MXCuBE. It includes methods for defining and emitting signals, allowing derived classes to customize signal emission based on their specific requirements.

>Strictly speaking it is the HardwareObject OR HardwareObjectYaml class (both inherit from HardwareObjectMixin). Once we unify the YAML and XML configuration this distinction should hopefully disappear.

### Emit

Signals are typically emitted when the state of a hardware object changes, such as when it becomes ready for operation, encounters an error, or completes a task. Additionally, signals may be emitted to indicate changes in parameters or settings of the hardware, such as new setpoints, values, or configuration options.

To emit a signal, derived classes can use the {py:meth}`mxcubecore.BaseHardwareObjects.HardwareObjectMixin.emit` method provided by the {py:class}`HardwareObject` class. This method takes the name of the signal as an argument and optionally includes additional data or parameters to pass along with the signal. This method calls the `dispatcher.send` method.


From the {py:class}`HardwareObjectMixin` class (removing extra lines for brevity):

```
    def emit(self, signal: Union[str, object, Any], *args) -> None:
        signal = str(signal)

        if len(args) == 1:
            if isinstance(args[0], tuple):
                args = args[0]
        dispatcher.send(signal, self, *args)
```

So, in a custom hardware object, since it inherits from {py:class}`HardwareObject`, one only needs to call: 
```
self.emit('my_signal', new_value)
```

### Receive

{py:class}`HardwareObjectMixin` implements the following ```connect```method, built around the homonymous method of _PyDispatcher_. Making it more convenient to use. The functions provides syntactic sugar: instead of ```self.connect(self, "signal", slot)``` it is possible to do ```self.connect("signal", slot)```.

From the {py:meth}`HardwareObjectMixin.connect` method (removing extra lines for brevity):

```
    def connect(
        self,
        sender: Union[str, object, Any],
        signal: Union[str, Any],
        slot: Optional[Callable] = None,
    ) -> None:
        """Connect a signal sent by self to a slot.

        Args:
            sender (Union[str, object, Any]): If a string, interprted as the signal.
            signal (Union[str, Any]): In practice a string, or dispatcher.
            Any if sender is a string interpreted as the slot.
            slot (Optional[Callable], optional): In practice a functon or method.
            Defaults to None.

        Raises:
            ValueError: If slot is None and "sender" parameter is not a string.
        """

        if slot is None:
            if isinstance(sender, str):
                slot = signal
                signal = sender
                sender = self
            else:
                raise ValueError("invalid slot (None)")

        signal = str(signal)

        dispatcher.connect(slot, signal, sender)

        self.connect_dict[sender] = {"signal": signal, "slot": slot}

        if hasattr(sender, "connect_notify"):
            sender.connect_notify(signal)
```

And an example usage on a custom hardware object would be:

```
    self.connect(some_other_hwobj, "a_signal", callback_method)
```

This assumes that `some_other_hwobj` is linked in the custom hardware object initialization, and `callback_method` must exist, otherwise an exception will happen once the signal is received.

If the sender hardware object has a method named `connect_notify`, it will be called on connect. Since this connect happens at application initialization, this typically triggers the emission of all signals during initialization, and thus all receivers start with the most recent value.


## Basic example

Given two hardware objects:

```
from mxcubecore.BaseHardwareObjects import HardwareObject
import gevent
from gevent import monkey; monkey.patch_all(thread=False)
import random
import datetime

"""
<object class="HO1">
</object>

"""
class HO1(HardwareObject):

    def __init__(self, name):
        super().__init__(name)
        self._value = 0.0
        self.run = False
    def get_value(self):
        return self._value

    def update_value(self):
        while self.run:
            _new_val = random.random()
            self._value = _new_val
            print(f'{datetime.datetime.now()} | valueChanged emitted, new value: {self._value}')
            self.emit("valueChanged", self._value)
            gevent.sleep(3)

    def start(self):
        self.run = True
        gevent.spawn(self.update_value)

    def stop(self):
        self.run = False	
```

and a data consumer:

```
from mxcubecore.BaseHardwareObjects import HardwareObject
import datetime
"""
<object class="HO2">
  <object hwrid="/ho1" role="ho1"/>
"""

class HO2(HardwareObject):

    def __init__(self, name):
        super().__init__(name)
        self._value = 0.0
        self.ho1 = None

    def init(self):
        self.ho1 = self.get_object_by_role("ho1")
        self.connect(self.ho1, "valueChanged", self.callback)

    def callback(self, *args):
        print(f'{datetime.datetime.now()} | valueChanged callback, arguments: {args}')
```

One could run both:

```
In [1]: from mxcubecore import HardwareRepository as hwr
   ...: hwr_dir='mxcubecore/configuration/mockup/test/'
   ...: hwr.init_hardware_repository(hwr_dir)
   ...: hwrTest = hwr.get_hardware_repository()
   ...: ho1 = hwrTest.get_hardware_object("/ho1")
   ...: ho2 = hwrTest.get_hardware_object("/ho2")
2024-03-18 12:20:18,434 |INFO   | Hardware repository: ['/Users/mikegu/Documents/MXCUBE/mxcubecore_upstream/mxcubecore/configuration/mockup/test']
+======================================================================================+
| role             | Class      | file                   | Time (ms)| Comment                   
+======================================================================================+
| beamline         | Beamline   | beamline_config.yml    | 9        | Start loading contents:   
| mock_procedure   | None       | procedure-mockup.yml   | 0        | File not found            
| beamline         | Beamline   | beamline_config.yml    | 9        | Done loading contents     
+======================================================================================+

In [2]: ho1.start()

2024-03-18 12:21:15.401871 | valueChanged emitted, new value: 0.7041173058901172
2024-03-18 12:21:15.402110 | valueChanged callback, arguments: (0.7041173058901172,)
2024-03-18 12:21:18.407419 | valueChanged emitted, new value: 0.39293503718591827
2024-03-18 12:21:18.407770 | valueChanged callback, arguments: (0.39293503718591827,)
2024-03-18 12:21:21.411648 | valueChanged emitted, new value: 0.8190801968640632
2024-03-18 12:21:21.411897 | valueChanged callback, arguments: (0.8190801968640632,)
2024-03-18 12:21:24.417379 | valueChanged emitted, new value: 0.5170546126120815
2024-03-18 12:21:24.418428 | valueChanged callback, arguments: (0.5170546126120815,)
2024-03-18 12:21:27.420696 | valueChanged emitted, new value: 0.27400475091220955
2024-03-18 12:21:27.421434 | valueChanged callback, arguments: (0.27400475091220955,)
2024-03-18 12:21:30.426785 | valueChanged emitted, new value: 0.3473955083798488
2024-03-18 12:21:30.427018 | valueChanged callback, arguments: (0.3473955083798488,)
2024-03-18 12:21:33.427715 | valueChanged emitted, new value: 0.9503048610962694
2024-03-18 12:21:33.427902 | valueChanged callback, arguments: (0.9503048610962694,)
In [3]: ho1.stop()
```

As you can see, the second hardware object receives and processes first one's signal.

> At least one entry must appear in the beamline's YAML configuration file. In this case I left the procedure mockup only, all the other mockups are commented. That is why only a few items appear in the loading table.

## General signals List

table with all the available signals, purpose, defined in abstract classes, known listeners...

### State related
| Signal                 | Description | Signature | Notes  |
| ---------------------- | ----------- | --------- | ------ |
| stateChanged | Notifies when the state has changed, new state value emitted      |  ('stateChanged', newState)   | |
| specificStateChanged | Notifies when a particular state has changed, new state value emitted      |  ('stateChanged', newState)   | Defined in HardwareObjectMixin, only used in AbstractDetector  |
| deviceReady | Notifies that the device is now ready      |  'deviceReady'  |  **Deprecated**|
| deviceNotReady | Notifies that the device is now not ready      |  'deviceNotReady'  |  **Deprecated**|
| equipmentReady | Notifies that the device is now ready      |  'equipmentReady'  |  **Deprecated**|
| equipmentNotReady | Notifies that the device is now not ready      |  'equipmentNotReady'  |  **Deprecated**|

### Value related
| Signal                 | Description | Signature | Notes  |
| ---------------------- | ----------- | --------- | ------ |
| valueChanged | Notifies when the value has changed      |  ('valueChanged', newValue)   | |
| update | Notifies when the value has changed      |  ('update', newValue)   | **Deprecated**|
| limitsChanged | Notifies when the limits have changed     |  ('limitsChanged', (low, high))   | |

### Data collection related
| Signal                 | Description | Signature | Notes  |
| ---------------------- | ----------- | --------- | ------ |
| energyScanStarted |    |  "energyScanStarted" | |
| energyScanFinished |   |  "energyScanFinished", dict: energyScanParameters   | |
| collectReady | collect hwobj readiness  |  "collectReady", bool  | |
| collectOscillationStarted |  | "collectOscillationStarted", (owner, sampleIid, sampleCode, sampleLocation, dataCollectParameters, oscId) | |
| collectOscillationFinished |  | "collectOscillationFinished", (owner, True, msgg, collectionId, oscId, dataCollectParameters) | |
| collectOscillationFailed |  | "collectOscillationFailed", (owner, False, msg, collectionId, osc_id)| |
| collectEnded |  | "collectEnded", (owner, bool, msg) | in AbstractMultiCollect|
| progressInit |  | "progressInit", ("Collection", 100, False)| |
| progressStop |  | "progressStop"| |
| collectImageTaken |   | ("collectImageTaken", frameNumber)  | |
| collectNumberOfFrames |   | ("collectNumberOfFrames", nframes, exposure_time) |in AbstractMultiCollect |

