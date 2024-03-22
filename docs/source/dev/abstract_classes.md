# Abstract Classes
## General Concept

The role of the mxcubecore Abstract Classes is to provide an API to be used by both mxcubeweb and mxcubeqt clients. It defines methods, attributes and signals. Most of the methods are defined only to give the footprint and should be, when appropriate, overloaded by the inheriting classes.

Abstract class can be inherited by any class, including another abstract class.
Any abstract class, if not inheriting from another abstract class should inherit from the **HardwareObject** or alternatively **HardwareObjectYam** class. The [hierarchy scheme](https://github.com/mxcube/mxcubecore/blob/develop/Hierarchy.pdf) shows in brief the inheritance of the abstract classes.

If get_value/set_value methods are defined in the abstract class, the name of the class defines what will be represented. For example, get_value/set_value in the AbstractEnergy will read/set the energy, while the wavelength, handled in the same class, will have specific methods like get_value_wavelemgth/set_value_wavelength.

## Methods

There are two methods, which are available for any class, as inherited from HardwareObject - **get_object_by_role()** and **get_property()**. Both methods allow to retrieve information from the configuration file (xml or yaml)
- get_object_by_role returns an object, associated to a role. Used to give an access to the defined Hardware Object.

  ```<object href="/aperture" role="beamsize"/>```
- get_property returns a property - numeric, string or None. This usually serves to define or asign different attributes.

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
The HardwareObjectState class is assigned to the STATES object, so it is accessible by the inheriting from HardwareObject classes as self.STATES.

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
The VALUES object is assigned to BaseValueEnum. In the inheriting from AbstractNState classes it is overloaded by simply getting the information from the configuration file.
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
Only the defined or overloaded in the class methods, attributes, signals and properties are listed. The exhaustive list of the available methods and properties for each class depends on the parent class.

### AbstractActuator

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractActuator.AbstractActuator` defines methods, common for any moving device.

Inherits from **HardwareObject** class.
  - defined methods:
    get_value, set_value, validate_value, update_value, _set_value, get_limits, update_limits
  - properties from the configuration file:
    actuator_name, username, read_only, default_value, default_limits
  - attributes:
    actuator_name, username, read_only, default_value, default_limits, unit, _nominal_value, _nominal_limits.
  - emitted signals:
    valueChanged, limitsChanged

The _set_value is the only abstract method that needs to be overloaded with every specific implementation.

### AbstractEnergy

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractEnergy.AbstractEnergy` handles energy and wavelength.

Inherits from **AbstractActuator** class.
  - methods:
    get_wavelength, get_wavelength_limits, set_wavelength, calculate_energy, calculate_wavelength
  - overloaded methods:
    update_value, force_emit_signals
  - attributes:
    is_tunable
  - emitted signals:
    energyChanged

### AbstractMotor

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractMotor.AbstractMotor` implement methods to handle devices which behave as a motor. Defines the MotorStaes enumeration, assigned to SPECIFIC_STATES.

Inherits from **AbstractActuator** class.
  - methods:
    get_velocity, set_velocity, set_value_relative, home
  - overloaded methods:
    update_value
  - properties from the configuration file::
    tolerance
  - attributes:
    _velocity, _tolerance

### AbstractNState

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractNState.AbstractNState` implements methods to handle devices with a fixed number of possible values.
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
  - attributes:
    get_dose_rate_per_photon_per_mmsq

### AbstractTransmission

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractTransmission.AbstractTransmission` get/set transmission value.

Defines the MotorStaes enumeration, assigned to SPECIFIC_STATES.

Inherits from **AbstractActuator** class.

The abstract class only defines the units and the limits at initialisation.


### AbstractBeam

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractBeam.AbstractBeam` implements methods to handle the beam size and shape and the presence of beam. Defines the BeamShape Enum to handle the shape of the beam.

Inherits from **HardwareObject** class.
  - methods:
    get_beam_size, get_beam_shape, get_beam_divergence, get_available_size, get_beam_position_on_screen, evaluate_beam_info, set_beam_size_shape, set_beam_position_on_screen
  - overloaded methods:
    re_emit_values
  - properties from the configuration file:
    beam_divergence_vertical, beam_divergence_horizontal
  - attributes:
    definer, aperture, slits, _beam_divergence, _beam_position_on_screen, _beam_width, _beam_height, ._beam_shape, _beam_label, _beam_size_dict
  - emitted signals:
    beamSizeChanged. beamInfoChanged, beamPosChanged

### AbstractShutter

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractShutter.AbstractShutter` implements methods to handle shutter like devices. Adds appropriate members to the BaseValueEnum.

Inherits from **AbstractNStater** class.
  - methods:
    open, close
  - attributes:
    is_open

## AbstractXRFSpectrum

The {py:class}`mxcubecore.HardwareObjects.abstract.AbstractXRFSpectrum.AbstractXRFSpectrum` implements methods to run XRF Spectrum type acquisition.

Inherits from **HardwareObject** class.
  - methods:
    start_xrf_spectrum, execute_xrf_spectrum, _execute_xrf_spectrum,
    spectrum_store_lims, spectrum_command_finished, spectrum_command_failed,
    spectrum_command_aborted, spectrum_status_change, spectrum_analyse,
    create_directory, get_filename.
  - properties from the configuration file:
    default_integration_time
  - attributes:
    lims, spectrum_info_dict, default_integration_time, spectrum_running
  - emitted signals:
    xrfSpectrumStatusChanged

_execite_xrf_scan is the only abstract method. It is a placeholder for specific  sequence implementation.
spectrum_analyse is additional hook to allow specific implementation.