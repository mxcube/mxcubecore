
from tango import DeviceProxy

def write_enum(dev, attr, value):
    values = list(dev.get_attribute_config(attr).enum_labels)

    no = values.index(value)
    if no >= 0:
        print("writing no %s for value %s (%s)" % (no,value, str(values)))

    dev.write_attribute(attr,no)

def read_enum(dev, attr):
    values = list(dev.get_attribute_config(attr).enum_labels)
    no = dev.read_attribute(attr).value
    return values[no]

dev = DeviceProxy("p11/simplon_detector/eh.01")
print( "before: ", read_enum(dev, "RoiMode"))
write_enum(dev,"RoiMode","disabled")
print( "after: ", read_enum(dev, "RoiMode"))
 
