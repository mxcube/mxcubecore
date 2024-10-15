# YAML configuration migration

Historically, MXCuBE used XML files for configuring hardware objects.
Now it's possible to use YAML files instead of XML files.
Currently, it is possible to use both XML and YAML files within the same beamline configuration.
You can use XML for some hardware objects and YAML for others.
This allows for a gradual migration to YAML configuration.

When using a YAML file, you may need to update the Python code of your hardware object.
Some of the methods for accessing hardware object configuration are not supported when using YAML.

This document provides some guidance on needed modification when migrating from XML to YAML.

## `beamline_config.yml` format changes

The format of the entry point configuration file `beamline_config.yml` have changed.
The old format had the following style:

```yaml
_initialise_class:
  class: mxcubecore.HardwareObjects.Beamline.Beamline
_objects:
  !!omap
  - session: session.xml
  - data_publisher: data_publisher.xml
  - machine_info: machine_info.xml

# Non-object attributes:
advanced_methods:
  - MeshScan
  - XrayCentering
tunable_wavelength: true
```

This format is not supported anymore.
The new format, corresponding to the example above, looks like this:

```yaml
class: mxcubecore.HardwareObjects.Beamline.Beamline
objects:
  !!omap
  - session: session.xml
  - data_publisher: data_publisher.xml
  - machine_info: machine_info.xml
configuration:
  advanced_methods:
    - MeshScan
    - XrayCentering
  tunable_wavelength: true
```

The changes to the format are outlined below.

### `_initialise_class`

The `_initialise_class` dictionary has been replaced by a `class` key-value pair.


### `_objects`

The `_objects` dictionary has been renamed to `objects`.
Otherwise, the format of the dictionary is the same as before.

### New `configuration` dictionary

All the general configuration parameters of the beamline have moved inside the new `configuration` dictionary.

## Converting XML files to YAML

Note that MXCuBE-Web provides some support for automatically converting XML configuration files to YAML.
See the [YAML configuration migration](https://mxcubeweb.readthedocs.io/en/latest/dev/yaml_conf_migration.html)
section in MXCuBE-Web documentation for details.
For details on the format of the YAML configurations file, see [Yaml-configured objects](configuration_files.md#yaml-configured-objects).

This section provides an example of equivalent configuration in XML and YAML formats.
Given the following XML configuration file:

```xml
<object class="Shanxi">
 <!-- configuration -->
 <simple_prop>prop_val</simple_prop>
 <nested>
   <child_a>uz</child_a>
   <child_b>ve</child_b>
 </nested>

 <!-- child objects -->
 <object role="session" href="/session"/>
 <object role="lims" href="/lims"/>
</object>
```

Gives the following equivalent configuration in YAML:

```yaml
class: Shanxi.Shanxi
configuration:
  simple_prop: prop_val
  nested:
    child_a: uz
    child_b: ve
objects:
  session: session.yaml
  lims: lims.yaml
```

The hardware object class specified by `<object class="Shanxi">` becomes the `class: Shanxi.Shanxi` key-value.
In the YAML format, the fully qualified class name must be specified.

All the configuration property XML tags becomes entries in the YAML's `configuration` dictionary.

Each `<object/>` tags becomes an entry in the YAML's `objects` dictionary.
The tag's `role` attribute is used as the entry's key name.
The tag's `href` attribute is converted to a config file name and specified as the entry's value.

## `self["prop_name"]` expressions not supported

Using index expressions to access configuration properties is no longer supported.
Use object's `config` attribute or `get_property()` methods.

For example, following old-style code:

```python
def init(self):
    foo = self["foo"]
```

Needs to be converted to one of the following styles:

```python
def init(self):
    # use 'config' attribute to access configuration property
    foo = self.config.foo
```

```python
def init(self):
    # use 'get_property()' method to access configuration property
    foo = self.get_property("foo")
```

## `@property` annotation for child objects

Using `@property` annotated attribute to provide access to a child object is not supported.

Consider this old-style code:

```python
class Shanxi(HardwareObject):
    def init(self):
        self._session = self.get_object_by_role("session")

    @property
    def session(self):
        return self._session
```

This code provides access to its child hardware object `session` via the annotated `session` attribute.
This style does not work anymore.
Remove the annotated `session` attribute and assignment to `self._session` attribute.
Use the following configuration file.

```yaml
class: Shanxi.Shanxi
objects:
  session: session.yml
```

During the initialization of the `Shanxi` object,
the child object will be automatically assigned to the `session` attribute.
See [Accessing child objects](configuration_files.md#accessing-child-objects) for more details.

## `name` parameter in `__init__` method

When a hardware object is loaded using a YAML configuration file, it is created with the following code:

```python
ClassName(name="role")
```

Thus, the hardware object's `__init__` method must accept the `name` parameter.
Below is an example that works with YAML configuration file:

```python
class Shanxi(HardwareObject):
    def __init__(self, name):
        super().__init__(name)
```

## `set_property()` method removed

The hardware object method `set_property()` has been removed.
It is no longer possible to set hardware object configuration properties from python code.
For static properties, move them to the hardware object configuration file.
If your code is setting properties dynamically,
you need to refactor the code to not rely on this deprecated feature.

## `<tangoname>` tag no longer supported

Previously it was possible to configure a hardware object's command and channels using this style:

```xml
<object class="SomeClass">
  <tangoname>some/tango/device</tangoname>
  <command type="tango" name="Open">Open</command>
  <channel type="tango" name="State" polling="1000">State</channel>
</object>
```

Above the tango device for commands and channels is specified with `<tangoname>` tag.
The `<tangoname>` tag is no longer supported and is ignored.
The tango device must be specified in each individual `<command>` and `<channel>` tag using the `tangoname` attribute.

The above example should be converted to the following style:

```xml
<object class="SomeClass">
  <command type="tango" name="Open" tangoname="some/tango/device">Open</command>
  <channel type="tango" name="State" tangoname="some/tango/device">State</channel>
</object>
```
