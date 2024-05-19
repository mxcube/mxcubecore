# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


import logging
import xml.sax
from xml.sax.handler import ContentHandler

from mxcubecore import BaseHardwareObjects


CURRENT_XML = None

new_objects_classes = {
    "equipment": BaseHardwareObjects.Equipment,
    "device": BaseHardwareObjects.Device,
    "procedure": BaseHardwareObjects.Procedure,
}


def parse(filename, name):
    """[summary]

    Args:
        filename ([type]): [description]
        name ([type]): [description]

    Returns:
        [type]: [description]
    """
    cur_handler = HardwareObjectHandler(name)

    global CURRENT_XML
    try:
        xml_file = open(filename)
        CURRENT_XML = xml_file.read()
    except Exception:
        CURRENT_XML = None

    xml.sax.parse(filename, cur_handler)

    return cur_handler.get_hardware_object()


def parse_string(xml_hardware_object, name):
    """[summary]

    Args:
        xml_hardware_object ([type]): [description]
        name ([type]): [description]

    Returns:
        [type]: [description]
    """
    global CURRENT_XML
    CURRENT_XML = xml_hardware_object
    cur_handler = HardwareObjectHandler(name)
    xml.sax.parseString(str.encode(xml_hardware_object), cur_handler)
    return cur_handler.get_hardware_object()


def load_module(hardware_object_name):
    """[summary]

    Args:
        hardware_object_name ([type]): [description]

    Returns:
        [type]: [description]
    """
    return __import__(hardware_object_name, globals(), locals(), [""])


def instanciate_class(module_name, class_name, object_name):
    """[summary]

    Args:
        module_name ([type]): [description]
        class_name ([type]): [description]
        object_name ([type]): [description]

    Returns:
        [type]: [description]
    """
    module = load_module(module_name)
    if module is None:
        return
    else:
        try:
            class_obj = getattr(module, class_name)
        except AttributeError:
            logging.getLogger("HWR").error(
                "No class %s in module %s", class_name, module_name
            )
        else:
            # check the XML
            if module.__doc__ is not None and CURRENT_XML is not None:
                i = module.__doc__.find("template:")

                if i >= 0:
                    xml_template = module.__doc__[i + 10 :]

                    xml_structure_retriever = XmlStructureRetriever()
                    xml.sax.parseString(CURRENT_XML, xml_structure_retriever)
                    current_structure = xml_structure_retriever.get_structure()
                    xml_structure_retriever = XmlStructureRetriever()
                    xml.sax.parseString(xml_template, xml_structure_retriever)
                    template_structure = xml_structure_retriever.get_structure()

                    if not template_structure == current_structure:
                        logging.getLogger("HWR").error(
                            "%s: XML file does not match the %s class template"
                            % (object_name, class_name)
                        )
                        return
            try:
                new_instance = class_obj(object_name)
            except Exception:
                logging.getLogger("HWR").exception(
                    "Cannot instanciate class %s", class_name
                )
            else:
                return new_instance


class HardwareObjectHandler(ContentHandler):
    def __init__(self, name):
        """[summary]

        Args:
            name ([type]): [description]
        """
        ContentHandler.__init__(self)

        self.name = name
        self.class_error = False
        self.objects = []
        self.reference = ""
        self.property = ""
        self.element_is_a_reference = False
        self.element_role = None
        self.buffer = ""
        self.path = ""
        self.previous_path = ""
        self.hwr_import_reference = None

    def get_hardware_object(self):
        """[summary]

        Returns:
            [type]: [description]
        """
        if self.hwr_import_reference is not None:
            return self.hwr_import_reference
        elif len(self.objects) == 1:
            return self.objects[0]

    def startElement(self, name, attrs):
        """[summary]

        Args:
            name ([type]): [description]
            attrs ([type]): [description]
        """
        if self.class_error:
            return

        self.buffer = ""

        if len(self.objects) == 0:
            object_name = self.name
        else:
            object_name = name

        assert not self.element_is_a_reference

        self.element_role = None
        self.property = ""
        self.command = {}
        self.channel = {}

        #
        # determine path to the new object
        #
        self.path += "/" + str(name) + "[%d]"
        i = self.previous_path.rfind("[")

        if i >= 0 and self.path[:-4] == self.previous_path[:i]:
            object_index = int(self.previous_path[i + 1 : -1]) + 1
        else:
            object_index = 1  # XPath indexes begin at 1

        self.path %= object_index

        _attrs = attrs
        attrs = {}

        for k in list(_attrs.keys()):
            v = str(_attrs[k])

            if v == "None":
                attrs[str(k)] = None
            else:
                try:
                    attrs[str(k)] = int(v)
                except Exception:
                    try:
                        attrs[str(k)] = float(v)
                    except Exception:
                        if v == "False":
                            attrs[str(k)] = False
                        elif v == "True":
                            attrs[str(k)] = True
                        else:
                            attrs[str(k)] = v
        if name == "hwr_import":
            self.hwr_import_reference = attrs["href"]

        if "role" in attrs:
            self.element_role = attrs["role"]
        if name == "device":
            # maybe we have to add the DeviceContainer mix-in class to each node of
            # the Hardware Object hierarchy
            i = len(self.objects) - 1
            while i >= 0 and not isinstance(
                self.objects[i], BaseHardwareObjects.DeviceContainer
            ):
                # newClass = new.classobj("toto", (self.objects[i].__class__,) + self.objects[i].__class__.__bases__ + (BaseHardwareObjects.DeviceContainer, ), {})
                # TODO replace deprecated DeviceContainerNode with a different class
                self.objects[i].__class__ = BaseHardwareObjects.DeviceContainerNode
                i -= 1

        #
        # is element a reference to another hardware object ?
        #
        ref = "hwrid" in attrs and attrs["hwrid"] or "href" in attrs and attrs["href"]
        if ref:
            self.element_is_a_reference = True
            self.reference = str(ref)

            if self.reference.startswith("../"):
                self.reference = "/".join(
                    self.name.split("/")[:-1] + [self.reference[3:]]
                )
            elif self.reference.startswith("./"):
                self.reference = "/".join(
                    self.name.split("/")[:-1] + [self.reference[2:]]
                )
            return

        if name in new_objects_classes:
            if "class" in attrs:
                module_name = str(attrs["class"])
                class_name = module_name.split(".")[-1]

                new_object = instanciate_class(module_name, class_name, object_name)

                if new_object is None:
                    self.class_error = True
                    return
                else:
                    new_object.set_path(self.path)
                    self.objects.append(new_object)
            else:
                new_object_class = new_objects_classes[name]
                new_object = new_object_class(object_name)
                new_object.set_path(self.path)

                self.objects.append(new_object)
        elif name == "command":
            if "name" in attrs and "type" in attrs:
                # short command notation
                self.command.update(attrs)
            else:
                # long command notation (allow arguments)
                self.objects.append(BaseHardwareObjects.HardwareObjectNode(object_name))
        elif name == "channel":
            if "name" in attrs and "type" in attrs:
                self.channel.update(attrs)
        else:
            if len(self.objects) == 0:
                if "class" in attrs:
                    module_name = str(attrs["class"])
                    class_name = module_name.split(".")[-1]

                    new_object = instanciate_class(module_name, class_name, object_name)

                    if new_object is None:
                        self.class_error = True
                        return
                else:
                    new_object = BaseHardwareObjects.HardwareObject(object_name)

                new_object.set_path(self.path)
                self.objects.append(new_object)
                """
                # maybe we can create a HardwareObject ? be strict for the moment...
                logging.getLogger("HWR").error("%s: unknown Hardware Object type (should be one of %s)", object_name, str(new_objects_classes.keys()))
                self.class_error = True
                return
                """
            else:
                new_object = BaseHardwareObjects.HardwareObjectNode(object_name)
                new_object.set_path(self.path)
                self.objects.append(new_object)

                self.property = name  # element is supposed to be a Property

    def characters(self, content):
        """[summary]

        Args:
            content ([type]): [description]
        """
        if self.class_error:
            return

        self.buffer += str(content)

    def endElement(self, name):
        """[summary]

        Args:
            name ([type]): [description]
        """
        if self.class_error:
            return

        name = str(name)

        if self.element_is_a_reference:
            if len(self.objects) > 0:
                self.objects[-1].add_reference(
                    name, self.reference, role=self.element_role
                )
                self.objects[0].add_reference(
                    name, self.reference, role=self.element_role
                )
        else:
            try:
                if name == "command":
                    if len(self.command) > 0:
                        if len(self.objects) > 0:
                            self.objects[-1].add_command(
                                self.command, self.buffer, add_now=False
                            )
                    else:
                        if len(self.objects) > 1:
                            self.objects[-2].add_command(
                                self.objects.pop(), add_now=False
                            )
                elif name == "channel":
                    if len(self.channel) > 0:
                        if len(self.objects) > 0:
                            self.objects[-1].add_channel(
                                self.channel, self.buffer, add_now=False
                            )
                elif name == self.property:
                    del self.objects[-1]  # remove empty object
                    self.objects[-1]._set_property(name, self.buffer)
                else:
                    if len(self.objects) == 1:
                        return

                    if len(self.objects) > 1:
                        self.objects[-2]._add_object(
                            name, self.objects[-1], role=self.element_role
                        )
                    if len(self.objects) > 0:
                        del self.objects[-1]
            except Exception:
                logging.getLogger("HWR").exception(
                    "%s: error while creating Hardware Object from XML file", self.name
                )

        self.element_is_a_reference = False
        self.element_role = None
        self.buffer = ""
        self.previous_path = self.path
        self.path = self.path[
            : self.path.rfind("/")
        ]  # remove last added name and suffix


class XMLStructure:
    def __init__(self):
        self.xmlpaths = set()
        self.attributes = {}

    def add(self, xml_path, attributes_set):
        """[summary]

        Args:
            xml_path ([type]): [description]
            attributes_set ([type]): [description]
        """
        self.xmlpaths.add(xml_path)

        if len(attributes_set) > 0:
            self.attributes[xml_path] = attributes_set

    def __eq__(self, s):
        """[summary]

        Args:
            s ([type]): [description]

        Returns:
            [type]: [description]
        """
        if self.xmlpaths.issubset(s.xmlpaths):
            for xml_path, attribute_set in self.attributes.items():
                try:
                    attribute_set_2 = s.attributes[xml_path]
                except KeyError:
                    return False
                else:
                    if not attribute_set.issubset(attribute_set_2):
                        return False

            return True
        else:
            return False


class XmlStructureRetriever(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)

        self.path = ""
        self.previous_path = ""
        self.current_attributes = set()
        self.structure = XMLStructure()

    def get_structure(self):
        """[summary]

        Returns:
            [type]: [description]
        """
        return self.structure

    def startElement(self, name, attrs):
        """[summary]

        Args:
            name ([type]): [description]
            attrs ([type]): [description]
        """
        self.path += "/" + str(name) + "[%d]"
        i = self.previous_path.rfind("[")

        if i >= 0 and self.path[:-4] == self.previous_path[:i]:
            index = int(self.previous_path[i + 1 : -1]) + 1
        else:
            index = 1  # XPath indexes begin at 1

        self.path %= index

        for attr, value in list(attrs.items()):
            if str(attr) == "hwrid":
                attr = "href"

            self.current_attributes.add("%s=%s" % (str(attr), str(value)))

    def endElement(self, name):
        """[summary]

        Args:
            name ([type]): [description]
        """
        self.structure.add(self.path, self.current_attributes)

        self.previous_path = self.path
        self.path = self.path[: self.path.rfind("/")]
