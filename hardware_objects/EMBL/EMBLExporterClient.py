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


"""EMBLExporterClient"""

from mx3core.BaseHardwareObjects import HardwareObject
from mx3core.Command import Exporter


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLExporterClient(HardwareObject):
    """EMBLExport client"""

    def __init__(self, *args):
        HardwareObject.__init__(self, *args)
        self.exporter_client = None

    def init(self):
        for client in Exporter.exporter_clients:
            self.exporter_client = Exporter.exporter_clients[client]
            return

    def get_client_info(self):
        """
        Returns client info
        :return:
        """
        for exporter_client in Exporter.exporter_clients:
            return exporter_client

    def get_method_list(self):
        """
        Returns lits with available methods
        :return: list
        """
        method_list = []
        for exporter_client in Exporter.exporter_clients:
            client = Exporter.exporter_clients[exporter_client]
            method_list.extend(client.get_method_list())
        return method_list

    def get_property_list(self):
        """
        Returns list with properties
        :return:
        """
        property_list = []
        for exporter_client in Exporter.exporter_clients:
            client = Exporter.exporter_clients[exporter_client]
            property_list.extend(client.get_propertyList())
        return property_list

    def read_property(self, property_name):
        """
        Returns property value
        :param property_name: str
        :return:
        """
        return self.exporter_client.readProperty(property_name)
