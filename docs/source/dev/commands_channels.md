# Commands and Channels

The mxcubecore provides a hardware object-level abstraction
for communicating using various flavors of control system protocols.
A hardware object can utilize instances of
[`CommandObject`](#mxcubecore.CommandContainer.CommandObject) and
[`ChannelObject`](#mxcubecore.CommandContainer.ChannelObject) objects.
These objects provide a uniform API for accessing a specific control system.
Mxcubecore provides support for using protocols such as
[_Tango_](https://www.tango-controls.org/),
[_EPICS_](https://docs.epics-controls.org),
_exporter_ and more.

The `CommandObject` and `ChannelObject` objects can be created using the `add_command()` and `add_channel()` methods of hardware objects.
Another option is to specify them in the hardware object's configuration file.
If `CommandObject` and `ChannelObject` are specified in the configuration file,
the specified objects will be automatically created during hardware object initialization.

## Configuration files format

The general format for specifying `CommandObject` and `ChannelObject` objects is as follows:

```yaml
class: <hardware-object-class>
<protocol>:                      # protocol in use, tango / exporter / epics / etc
  <end-point>:                   # tango device / exporter address / EPICS prefix / etc
    commands:
      <command-1-name>:          # command's MXCuBE name
        <config-prop-1>: <val-1>
        <config-prop-2>: <val-2>
    channels:
      <channel-1-name>:          # channel's MXCuBE Name
        <config-prop-1>: <val-1>
        <config-prop-2>: <val-2>
```

The `CommandObject` and `ChannelObject` specification are grouped by the protocol they are using.
Each protocol have its own dedicated section in the configuration file.
The semantics for the protocol are similar but protocol-specific, see below for details.

Currently, the following protocols can be configured using YAML configuration files:

 - [Tango](#tango-protocol)
 - [exporter](#exporter-protocol)
 - [EPICS](#epics-protocol)

## Tango Protocol

The format for specifying _tango_ `CommandObject` and `ChannelObject` objects is as follows:

```yaml
class: <hardware-object-class>
tango:
  <tango-device-name>:
    commands:
      <command-1-name>:
        <config-prop-1>: <val-1>
      <command-2-name>:
        <config-prop-1>: <val-1>
    channels:
      <channel-1-name>:
        <config-prop-1>: <val-1>
        <config-prop-2>: <val-2>
      <channel-2-name>:
        <config-prop-1>: <val-1>
```

`<tango-device-name>` specifies the tango device to use.
Multiple `<tango-device-name>` sections can be specified, in order to use different tango devices.
Each `<tango-device-name>` contains optional `commands` and `channels` sections.
These sections specify `CommandObject` and `ChannelObject` object to create using the `<tango-device-name>` tango device.

### Commands

`commands` is a dictionary where each key specifies a `CommandObject` object.
The key defines the MXCuBE name for the command.
The values specify an optional dictionary with configuration properties for the `CommandObject` object.
The following configuration properties are supported:

| property | purpose            | default             |
|----------|--------------------|---------------------|
| name     | tango command name | MXCuBE command name |

### Channels

`channels` is a dictionary where each key specifies a `ChannelObject` object.
The key defines the MXCuBE name for the channel.
The values specify an optional dictionary with configuration properties for the `ChannelObject` object.
The following configuration properties are supported:

| property       | purpose                            | default             |
|----------------|------------------------------------|---------------------|
| attribute      | tango attribute name               | MXCuBE channel name |
| polling_period | polling periodicity, milliseconds  | polling is disabled |
| timeout        | tango device timeout, milliseconds | 10000               |

By default, a tango `ChannelObject` object will use tango attribute change event, in order to receive new attribute values.
For this to work, the tango device must send the change events for the attribute.
For cases where such events are not sent, the attribute polling can be enabled.
If `polling` property is specified, MXCuBE will poll the tango attribute with specified periodicity.

### Example

Below is an example of a hardware object that specifies Tango commands and channels.

```yaml
class: MyTango
tango:
  some/tango/device:
    commands:
      Open:
      Close:
      Reset:
        name: Reboot
    channels:
      State:
      Volume:
          attribute: currentVolume
          poll: 1024
```

In the above example, commands `Open`, `Close` and `Reset` as well as channels `State` and `Volume` are configured.
All command and channel objects are bound to the commands and attributes of the _some/tango/device_ tango device.

`Open` and `Close` commands are bound to _Open_ and _Close_ Tango commands.
The `Reset` has a configuration property that binds it to _Reboot_ tango command.

The `State` channel will be mapped to _State_ attribute of the Tango device.
Its value will be updated via Tango change events.

The `Volume` channel will be mapped to the _currentVolume_ attribute of the tango device.
The _currentVolume_ attribute's value will be polled every 1024 milliseconds.

## Exporter Protocol

The format for specifying _exporter_ `CommandObject` and `ChannelObject` objects is as follows:

```yaml
class: <hardware-object-class>
tango:
  <exporter-address>:
    commands:
      <command-1-name>:
        <config-prop-1>: <val-1>
      <command-2-name>:
        <config-prop-1>: <val-1>
    channels:
      <channel-1-name>:
        <config-prop-1>: <val-1>
      <channel-2-name>:
        <config-prop-1>: <val-1>
```

`<exporter-address>` specifies the exporter address to use.
Multiple `<exporter-address>` sections can be specified to use devices at different addresses.
Each `<exporter-address>` contains optional `commands` and `channels` sections.
These sections specify `CommandObject` and `ChannelObject` objects to create using the `<exporter-address>` tango device.

`<exporter-address>` specifies the exporter's host and port number.
It has the following format: `<host>:<port>`.
`<host>` is the host name or IP address to use.
`<port>` is the TCP port number to use.
Note that, due to YAML parsing rules, you need to use quotes when specifying the exporter address.
Below is an example of an exporter address that can be used in a YAML configuration file:

```
"foo.example.com:9001"
```

### Commands

`commands` is a dictionary where each key specifies a `CommandObject` object.
The key defines the MXCuBE name for the command.
The values specify an optional dictionary with configuration properties for the `CommandObject` object.
The following configuration properties are supported:

| property | purpose               | default             |
|----------|-----------------------|---------------------|
| name     | exporter command name | MXCuBE command name |

### Channels

`channels` is a dictionary where each key specifies a `ChannelObject` object.
The key defines the MXCuBE name for the channel.
The values specify an optional dictionary with configuration properties for the `ChannelObject` object.
The following configuration properties are supported:

| property  | purpose                  | default             |
|-----------|--------------------------|---------------------|
| attribute | exporter attribute name  | MXCuBE channel name |

### Example

Below is an example of a hardware object that specifies exporter commands and channels.

```yaml
class: MyExporter
exporter:
  "foo.example.com:9001":
    commands:
      Open:
      Close:
      Reset:
        name: Reboot
    channels:
      State:
      Volume:
          attribute: currentVolume
```

In the above example, commands `Open`, `Close` and `Reset` as well as `State` and `Volume` channels are configured.
All command and channel objects are bound to the exporter host _foo.example.com_ at port _9001_.

`Open` and `Close` commands are bound to _Open_ and _Close_ exporter commands.
The `Reset` has a configuration property that binds it to the _Reboot_ exporter command.

The `State` channel will be mapped to _State_ exporter attribute.
The `Volume` channel will be mapped to _currentVolume_ exporter attribute.

## EPICS Protocol

The format for specifying _EPICS_ `ChannelObject` objects is as follows:

```yaml
class: EpicsCommunicator
epics:
  <prefix>:
    channels:
      <channel-1-name>:
        <config-prop-1>: <val-1>
        <config-prop-2>: <val-2>
      <channel-2-name>:
        <config-prop-1>: <val-1>
```

`<prefix>` specifies the EPICS PV prefix to use for that section.
Multiple `<prefix>` sections can be specified, in case not all channels share a common prefix.
Each `<prefix>` contains a `channels` section, which specifies `ChannelObject` objects to create.

It is also possible to use the empty string, `""`, as the prefix.
This is useful in cases where none of the channels share a common prefix.
See [below](#pv-names) for details on how channel PV names are determined.

### Channels

`channels` is a dictionary where each key specifies a `ChannelObject` object.
The key defines the MXCuBE name for the channel.
The values specify an optional dictionary with configuration properties for the `ChannelObject` object.
The following configuration properties are supported:

| property | purpose               | default             |
|----------|-----------------------|---------------------|
| suffix   | PV name suffix        | MXCuBE channel name |
| poll     | polling periodicity   |                     |

#### PV names

The PV name of a channel is determined by concatenating its section's prefix and the specified `suffix`.
If no suffix is specified, the channel's MXCuBE name is used in place of the `suffix`.
Observe an example configuration below:

```yaml
class: EpicsCommunicator
epics:
  "FOO:B:":
    channels:
      State:
        suffix: pv_1.STAT
      Vol:
        suffix: volume.VAL
      Freq:
```

Her we have an `FOO:B:` prefix specified, with channels `State`, `Vol` and `Freq`.
The `State` channel will use `FOO:B:pv_1.STAT` PV name, specified by section's prefix and the `suffix` configuration property.
The `Vol` channel's PV name will be`FOO:B:volume.VAL`.
The `Freq` channel's PV name becomes `FOO:B:Freq`, specified by section's prefix and channel's MXCuBE name.

### Example

Below is an example of a hardware object that specifies EPICS channels.

```yaml
class: EpicsCommunicator
epics:
  "MNC:B:PB04.":
    channels:
      State:
      Volume:
          suffix: vlm
          poll: 512
```

In the above example channels `State` and `Volume` are configured.
The `State` channel will be mapped to PV name _MNC:B:PB04.State_.
The `Volume` channel will be mapped to PV name _MNC:B:PB04.vlm_.
For `Volume` channel, polling will be enabled.
