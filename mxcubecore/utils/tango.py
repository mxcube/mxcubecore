from tango import DevFailed

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.Command.Tango import TangoChannel


class TangoAttributeReadError(Exception):
    def __init__(self, attribute_name: str):
        super().__init__()
        self.attribute_name = attribute_name


def add_attribute_channel(
    hwo: HardwareObject,
    tango_device: str,
    attribute_name: str,
    polling: int | None = None,
    update_callback=None,
) -> TangoChannel:
    """Utility function to add Tango attribute Channel to a hardware object.

    This function adds a Channel object to specified hardware object and checks
    that it's possible to read the specified tango attribute.

    If there is errors reading the attribute, the TangoAttributeReadError
    exception is raised.

    Parameters:
        hwo: The hardware object where to add the Channel object.
        tango_device: Tango device name.
        attribute_name: The tango attribute name.
        polling: Attribute polling periodicity.
        update_callback: Optional callback, if provided it is connected to
           "update" signal of Channel object
    """

    channel = hwo.add_channel(
        {
            "type": "tango",
            "tangoname": tango_device,
            "name": attribute_name,
            "polling": polling,
        },
        attribute_name,
    )

    if not channel.is_connected():
        raise TangoAttributeReadError(attribute_name)

    #
    # check if it's possible to read the Attribute
    #
    try:
        val = channel.get_value()
    except DevFailed:
        raise TangoAttributeReadError(attribute_name) from None

    #
    # add "update" callback
    #
    if update_callback is not None:
        channel.connect_signal("update", update_callback)
        #
        # We have 'consumed' the initial value of this channel above,
        # when we were testing if it's readable. The standard polling
        # will not invoke the callback with that value now.
        # Make sure initial value is passed to the callback.
        #
        update_callback(val)

    return channel
