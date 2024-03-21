# Abstract Classes
## General Concept

The role of the mxcubecore Abstract Classes is to provide an API to be used by both mxcubeweb and mxcubeqt clients. It defines methods, properties and signals. Most of the methods are defined only to give the footprint and shold be, wneh appropriate, overloaded by the inheriting classes.

Abstract class can be inherited by any class, including another abstract class.
Any abstract calss, if not inheriting from another abstract class should inherit from the **HardwareObject** class.

If get_value/set_value methods are defined in the abstract class, the name of the class defines what will be represented. For example get_value/set_value in the AbstractEnergy will read/set the enery, while the wavelength, handled in the same class, will have specific methoods for its reading/setting.

## Methods

There are two methods, which are avaiable for any class, as inherited from HardwareObject - **get_object_by_role()** and **get_property()**. Both methods allow to retrieve information from the configuration file (xml or yaml)
- get_object_by_role returns an object, associated to a role

  ```<object href="/aperture" role="beamsize"/>```
- get_property returns a property - numeric, string or None

  ```<values>{"IN": False, "OUT": True}</values>```

Methods, specific to different abstract classes will be listed further.


## STATES and SPECIFIC_STATES Enum
There is only a limited number of general states, shared by all HardwareObjects.
They are defined as an Enum as follows and should not be overridden.
```
@enum.unique
class HardwareObjectState(enum.Enum):
    """Enumeration of common states, shared between all HardwareObjects"""

    UNKNOWN = 0
    WARNING = 1
    BUSY = 2
    READY = 3
    FAULT = 4
    OFF = 5
```
The HardwareObjectState class is asigned to the STATES object, so in the inheriting from HardwareObject classes it is accessible as self.STATES

In case additional states for a specific implementation are needed, there is a placeholder enumeration.

```
class DefaultSpecificState(enum.Enum):
    UNKNOWN = "UNKNOWN"
```
Similar to STATES, a SPECIFIC_STATES object allows to access the specific states, without knowing the name of the class where they are defined.

## VALUES Enum and how to expand it.
Another abstraction concept is the enumeration for the values, which can be get/set. It allows to define any value as an Enum, so only the name is fixed, but the value itself is flexible. It is defined in the AbstractNState.py with just one member:
```
class BaseValueEnum(enum.Enum):
    """Defines only the compulsory unknown."""

    UNKNOWN = "UNKNOWN"
```
The VALUES object is asigned to BaseValueEnum. In the inheriting from AbstractNState classes it is overloaded by simply getting the information from the configuration file.
For example, from the following configuration
```
<values>{"A10": (0, 10, 0.15), "A20": (1, 20, 0.3), "A30": (2, 30, 0.63), "A50": (3, 50, 0.9), "A75": (4, 75, 0.96)}</values>
```

The python code transforms the string from the configuration to an Enum:
```
values = ast.literal_eval(self.get_property("values"))
values_dict = dict(**{item.name: item.value for item in self.VALUES})
values_dict.update(values)
self.VALUES = Enum("ValueEnum", values_dict)
```
This is the same as if a ValueEnum class was defined as follows:
```
class ValueEnum(enum.enum):
   A10 = (0, 10, 0.15)
   A20 = (1, 20, 0.3)
   A30 = (2, 30, 0.63)
   A50 = (3, 50, 0.9)
   A75 = (4, 75, 0.96)
```

## Timeout
A timeout parameter can be added to any method, which needs it. The common behaviour is defined as:

 - timeout=0 - return immediately, without waiting
 - timeout=None - wait until the end of the action
 - timeout=n - wait for n seconds (float value). Raise an exception if error.

## Abstract Classes
Only the defined or overloaded in the class methods and properties are listed. The exhaustive list of the available methods and properties for each class depeds on the parent class.

### AbstractActuator

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractActuator.AbstractActuator` defines methods, common for any moving device.

Inherits from **HardwareObject** class.
  - defined methods:
    get_value, set_value, validate_value, update_value, _set_value, get_limits, update_limits, re_emit_values, force_emit_signals
  - properties:
    actuator_name, username, read_only, default_value, default_limits, unit
  - emited signals:
    valueChanged. stateChanged, limitsChanged

The _set_value is the only abstract method that needs to be overloaded with every specific implementation.

### AbstractEnergy

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractEnergy.AbstractEnergy` handles the energy and wavelength.

Inherits from **AbstractActuator** class.
  - methods:
    get_wavelength, get_wavelength_limits, set_wavelength, calculate_energy, calculate_wavelength
  - properties:
    is_tunable
  - emited signals:
    valueChanged

### AbstractMotor

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractMotor.AbstractMotor` implement methods to handle devices which behave as a motor. Defines the MotorStaes enumeration, assigned to SPECIFIC_STATES.

Inherits from **AbstractActuator** class.
  - methods:
    get_velocity, set_velocity, set_value_relative, home
  - properties:
    tolerance
  - emited signals:
    valueChanged

### AbstractNState

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractNState.AbstractNState` implemets methods to handle devices with a fixed number of possible values.
Defines the BaseValueEnum, assigned to VALUES.

Inherits from **AbstractActuator** class.
  - methods:
    initialise_values, value_to_enum
  - overloaded methods:
    validate_value, set_limits, update_limits, re_emit_values

### AbstractFlux

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractFlux.AbstractFlux` handle the flux. Defines get_dose_rate_per_photon_per_mmsq as dose rate for a standard composition crystal, in Gy/s as a function of energy in keV.

Inherits from **AbstractActuator** class.
  - methods:
    get_average_flux_density
  - properties:
    get_dose_rate_per_photon_per_mmsq

### AbstractTransmission

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractTransmission.AbstractTransmission` get/set transmission value.

Defines the MotorStaes enumeration, assigned to SPECIFIC_STATES.

Inherits from **AbstractActuator** class.

The abstract class only defines the units and the limits at initialisation.


### AbstractBeam

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractBeam.AbstractBeam` defines methods to handle the beam size and shape and the presence of beam.

Inherits from **HardwareObject** class.
  - methods:
    get_beam_size, get_beam_shape, get_beam_divergence, get_available_size, get_beam_position_on_screen, evaluate_beam_info, set_beam_size_shape, set_beam_position_on_screen
  - properties:
    definer, aperture, slits
  - emited signals:
    beamSizeChanged. beamInfoChanged, beamPosChanged
