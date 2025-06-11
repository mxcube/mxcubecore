# Configuration files

The MXCuBE core is organised as a tree of *HardwareObjects*,
and configuration is organised with a file per HardwareObject.
The (mandatory) topmost object in the tree is the *Beamline* object,
which is configured in the `beamline_config.yml` file.
This in turn contains the names of other configuration files,
recursively, which may be a mixture of YAML and XML configuration files.
The Beamline object can be accessed as an attribute of the HardwareRepository module
(`HardwareRepository.beamline`).
As of 2024-03-14 MXCuBE is in the middle of a change-over to a new system for configuration
that uses YAML files instead of XML files,
which has different ways of accessing the configuration data from inside the code.
HardwareObjects can be configured to contain both other hardware objects and properties.
The former are identified relative to the container by a role.

## Finding the files
Configuration files are searched for by name in a series of directories given as a lookup path.

In mxcubeqt this is specified either with the `--coreConfigPath` command line parameter to MXCuBE,
or through the `MXCUBE_CORE_CONFIG_PATH` environment variable.

In mxcubeweb the configuration lookup path is specified with the `--repository` option to `mxcube-server`,
the default being `mxcubeweb/test/HardwareObjectsMockup.xml/`,
where the mxcubeweb mock configuration resides.

There is a set of configuration data under the `mxcubecore/mxcubecore/configuration` directory.
This includes the `mockup/` directory
with `qt/` and `gphl/` subdirectories for mock mxcubeqt operation.
There is also a directory with configuration for each beamline,
but these are mostly not up to date.
The actual beamline configuration files are mostly held in a separate (and non-comitted) directory at the beamlines.

## Yaml-configured objects
### Code and file structure
Each YAML-configured object has a `name` attribute,
which is equal to the role that identifies the object within the containing object
(the name of the Beamline object is `beamline`).

The most complete example of a YAML-configured object is the `Beamline` object.
The comments in `beamline_config.yml` are the best guide to the syntax of YAML configuration files.
It is a key principle of YAML-configured classes that **all** attributes
added in the configuration must match a pre-defined attribute coded in the class.
This means that you can look in the class code to see which attributes are available.

The only exception is the `class` attribute at the start of the YAML configuration file.
This attribute specifies the import name of the class that is to be created.

The `objects` dictionary in the file gives the HardwareObjects that are contained in
(i.e. children of) the object.
The dictionary key is the role name, and the value is the name of the configuration file.
Each `role_name` must match a read-only property coded in the body of the class.
Note that classes are loaded and initialised in the order given by this list,
so that there is a reproducible loading order.
Contained objects can be defined as procedures, so that they are added to the list of procedures.
Each YAML-configured class has an `_init()` method that is executed immediately after the object is created,
and an `init()` function that is executed after configured parameters and contained objects have been loaded.

Below is an example YAML configuration file:

```yaml
class: Orkhon.Erdenet
configuration:
  altai: big
  choir: 52
objects:
  darkhan: darkhan.yaml
  session: session.yaml
tango:
  "some/tango/device":
    commands:
      Open:
      Close:
    channels:
      State:
```

This file specifies a hardware object, which is an instance of the `Erdenet` class from `Orkhon` module.
That object will have two configuration properties `altai` and `choir`.
Two child objects with roles `darkhan` and `session` will be loaded from the specified configuration files.
The hardware object will also have access to command objects `Open` and `Close`, and a `State` channel object.
See [Commands and Channels](commands_channels.md) section for details on how to specify command and channel bindings.

### Accessing configuration properties

The contents of the `configuration` section will be available as a `config` attribute of the hardware object.
It is also possible to access the configuration with the `get_property()` and `get_properties()` methods.
Below is an example of how configuration can be read in the `init()` method of a hardware object.

```python
def init(self):
    # access 'file_info' config property via 'config' attribute
    file_info = self.config.file_info

    # access 'file_info' config property via 'get_property()' method
    file_info = self.get_property("file_info")

    # get all of the object's config properties
    all_props = self.get_properties()
```

Note that you should only access an object's configuration properties from its implementation class.
The values of an object's configuration properties are considered implementation details of that hardware object.
If access is required by outside code, then it should be provided by the object's client API.

### Accessing child objects

The `objects` dictionary in the YAML configuration file specifies the child objects.
These child objects can be accessed via the parent object's `role_name` attribute.
For example, if a hardware object is configured with this configuration file:

```yaml
class: Foo.Foo
objects:
  bar: gazonk.yaml
```

An instance of the `Foo` class will be created.
This instance will have a child object with `bar` role, with configuration from `gazonk.yaml` file.
That child object will be accessible with `foo.bar` python expression, where `foo` is the parent object.

The Beamline object (`HardwareRepository.beamline`) is a YAML-configured object,
and is the starting point for finding other hardware objects.
These may in turn contain other objects, so you can do e.g.
`HardwareRepository.beamline.detector.distance` to get the detector distance motor object.


## XML-configured objects
### Code and file structure
XML-configured objects have a `name()` method,
that returns the name of the configuration file used to specify it (without the `.xml` suffix).
It is this name that is used in internal data structures and a number of access functions.

XML-configured objects must be subclasses of the `BaseHardwareObjects.HardwareObject` class.
A good example is `mxcubecore/configuration/mockup/detector-mockup.xml`
(note that `hwrid` is an alias for what is normally written as `href`).
In XML configuration contained objects are given using the "object" element,
with the `href` attribute giving the configuration file name to pick up
(you can use a similar syntax to redirect the topmost element to another file)
and the `role` attribute giving the role name.
Simple properties are given as contained XML elements,
and complex properties (dictionaries) are given as elements of type 'object' without a 'href' attribute.


The configuration data are kept in complex internal data structures,
with links back to the original XML.

The important methods can be found in the `BaseHardwareObjects,HardwareObjectNode` class.
XML-configured files have no limits on the attributes or objects they can contain.
This leads to greater flexibility, since you can add a new attribute when needed without modifying the class code;
it also means that there is no way to check which attributes are supported without looking into the configuration files,
and gives more scope for local and potentially conflicting implementations.
The functions have quite complex behaviour that amounts to overloading.

### Accessing configuration data

The recommended way to access contained objects is through the `get_object_by_role` function,
since it works on role names rather than the less predictable file names.
As implemented the function will look recursively in contained objects for a given role name
if the topmost object does not contain it.
The `get_roles` method returns a list of roles that are defined on the object itself.

You can get and set the values of simple properties by normal `obj.attr` syntax,
which will also get you normal, non-property attributes.
The `get_properties` method returns a dictionary of all properties and their values,
and the `get_property` method behaves as `get_properties().get`.
Direct setting of properties internally calls the `_set_property` function,
and this function automatically converts strings to `int`, `float` or `bool` if possible.

There are additional ways of accessing contained objects.
`_get_objects` and `has_object` take as input the object name
As currently coded (was it always thus?) the name is equal to the role name used to add the object.
An XML-configured object is also coded to mimic a Python list and dictionary of contained objects,
so that `anObject[ii]`
(`ii` being an integer) returns the `ii`'th contained object,
whereas `anObject[key]` (key being a string) returns the contained object defined by the name (i.e. the role name).

For XML-configured HardwareObjects (but not for YAML:-configured ones)
there are two additional ways of getting hold of HardwareObjects.

Beamline.get_hardware_object lets you get a HO from a dotted list of rolenames (e.g. 'detector.distance')
This is essentially a convenience function to avoid repeated get_object_by_role calls.
For YAML-configured objects the same could be done by direct attribute access.

HardwareReposotory.get_hardware_object, on the other hand,
lets you access hardware objects by the name of the configuration file,
loading the file if it has not been loaded already.
Use of this function requires you to hardwire the names of configuration files in the code.
