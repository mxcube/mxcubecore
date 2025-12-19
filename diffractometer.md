Within the concept of the AbstractDiffractometer there are certain number of roles, which are fixed and define a corresponding motor or nstate actuator object.

This allows them to be used in a standard way by the MXCuBE application (web or Qt).

We also introduce a convention about the direction of the alignment and centring motors:

- x axis is parallel to the beam. Positive direction is from right to left.
- y axis is perpendicular to the beam, parallel to the ground. Positive direction is from left to right, facing the beam.
- z axis is perpendicular to the floor. Positive direction is top down.

Here follows the list of the fixed roles and the description of the corresponding objects, accessible via beamline.diffractometer hardware object.

1\. Motor objects (roles) and their functionality:

- **omega** - the rotation axis, independent of the orientation (up, down or side). Positive direction is clockwise
- **sampx** - centring table x axis
- **sampy** - centring table y axis
- **focus** - alignment table x axis
- **phiy** - alignment table y axis
- **phiz** - alignment table z axis
- **sample_horizontal** - x axis, combination of sampx and sampy. Equivalent to sampx at omega=0 and sampy for omega=90.
- **sample_vertical** - y axis, combination of sampx and sampy. Equivalent to sampy at omega=0 and sampx for omega=90.
- **backlight** - adjust the intensity of the back light
- **frontlight** - adjust the intensity of the front light

2\. Discrete (N) state equipment and its functionality:

- **zoom** - zoom levels
- **fshutter** - fast shutter - allow beam on the sample
- **beamstop** - put in front of a detector to avoid the direct beam.
- **capillary** - if present, a tube to reduce the scattering background.
- **backlightswitch** - move the backlight on the level of the onaxis viewer
- **frontlightswitch** - switch on/off the front light
- **fluo_detector** - if present, actuator to move a fluorescence detector close to the sample

Possibly there is equipment physically part of the diffractometer, but not accessed via beamline.diffractometer:

- aperture - Device to define the beam size - beamline.beam.aperture
- cryostream - beamline.cryo
