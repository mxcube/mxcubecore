In mxcubecore there are two classes, which could be seen as approximate abstractions for controlling a diffractometer - ***MiniDiff*** and ***GenericDiffractometer***. These classes handle also some sample view and sample centring functionalities. There is also an ***AbstractSampleView*** class, which contains only few methods, used to handle the sample visualisation.

The new **AbstractDiffractometer** class and the refactoring of the **AbstractSampleView/SampleView** classes aim to make a standard diffractometer API as well as group all the sample viewing methods to the sample view classes. This intorduces some breaking changes.

#### A convention has been introduced for the motors of the diffractometer.

Thus, the object names change as follows:

- **MiniDiff**:
  - phiMotor - omega
  - sampleXMotor - sampx
  - sampleYMotor - sampy
  - phiyMotor - phiy
  - phixMotor - phiz
  - kappaMotor - kappa
  - kappaPhiMotor - kappa_phi
  - zoomMotor - zoom, as NState, not as motor
- **GenericDiffractometer**:
  - phi - omega

#### Transfer of all the sample view and centring methods to the sample view objects, including the list of the sample centring motors.

This implies that some methods are invoked not as HWR.beamline.diffractometer, but as HWR.beamline.sample_view. Here follows the list of these methods:

- take_snapshot
- get_centring_status
- get_positions
- get_centred_point_from_coord
- motor_positions_to_screen
- current_centring_procedure
- cancel_centring_method
- accept_centring
- reject_centring

#### The centring motors are defined in sample_view and not diffractometer any more.

They are defined in the sample_view configuration file, which also defines their directions and the centring_reference_position. The motors have the same roles as the diffractometer and are hold in the centring_motors dictionary. The motors change as follows:

- centringPhi - centring_motors["omega"]
- centringPhiy - centring_motors["phiy"]
- centringPhiz - centring_motors["phiz"]
- centringSamplex - centring_motors["sampx"]
- centringSampley - centring_motors["sampy"]

#### Some methods and global variables, used by the centring and defined in the diffractometer have been removed.

Instead, a specific method for each type of centring has been introduced. The relevant method is set by the queue. Thus:

- CENTRING_METHOD_MANUAL - replaced by start_manual_centring()
- C3D_MODE - replaced by start_auto_centring()
- start_centring_method - removed
- cancel_centring_method - removed

#### Methods name change

- *set_value_motors* replaces move_motors
- *get_phase* replaces get_current_phase
- *self.omega.set_value_relative* replaces move_omega_relative

### Some methods have been converted to properties

- in_plate_mode
- in_kappa_mode
