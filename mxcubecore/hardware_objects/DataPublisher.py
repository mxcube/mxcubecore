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
import redis
import json
import gevent
import logging

from enum import Enum, unique

from mxcubecore.BaseHardwareObjects import HardwareObject


@unique
class PlotType(Enum):
    """
    Defines default plot
    """

    SCATTER = "scatter"


class PlotDim(Enum):
    """
    Defines data dimension
    """

    ONE_D = 1
    TWO_D = 2


class DataType(Enum):
    """
    Defines avialable data types
    """

    FLOAT = "float"


class FrameType(Enum):
    """
    Enum defining the message frame types
    """

    DATA = "data"
    START = "start"
    STOP = "stop"


def one_d_data(x, y):
    """
    Convenience function for creating x, y data
    """
    return {"x": x, "y": y}


def two_d_data(x, y):
    """
    Convenience function for creating x, y, z data
    """
    return {"x": x, "y": y, "z": z}


class DataPublisher(HardwareObject):
    """
    DataPublisher handles data publishing
    """

    def __init__(self, name):
        super(DataPublisher, self).__init__(name)
        self._r = None
        self._subsribe_task = None

    def init(self):
        """
        FWK2 Init method
        """
        super(DataPublisher, self).init()

        rhost = self.get_property("host", "localhost")
        rport = self.get_property("port", 6379)
        rdb = self.get_property("db", 11)

        self._r = redis.Redis(
            host=rhost, port=rport, db=rdb, charset="utf-8", decode_responses=True
        )

        if not self._subsribe_task:
            self._subsribe_task = gevent.spawn(self._handle_messages)

    def _handle_messages(self):
        """
        Listens for published data and handles the data.
        """
        pubsub = self._r.pubsub(ignore_subscribe_messages=True)
        pubsub.psubscribe("HWR_DP_NEW_DATA_POINT_*")

        _data = {}

        # The descriptions of active sources for fast access
        # while publishing data
        active_source_desc = {}

        for message in pubsub.listen():
            if message:
                try:
                    redis_channel = message["channel"]
                    _id = redis_channel.split("_")[-1]

                    data = json.loads(message["data"])

                    if data["type"] == FrameType.START.value:
                        _data[redis_channel] = {"x": [], "y": []}

                        self._update_description(_id, {"running": True})

                        # Clear previous data so that we are not acumelating
                        # with previously published data
                        self._clear_data(_id)

                        self.emit(
                            "start", self.get_description(_id, include_data=True)[0]
                        )

                        active_source_desc[redis_channel] = self._get_description(_id)

                    elif data["type"] == FrameType.STOP.value:
                        self._update_description(_id, {"running": False})
                        self.emit(
                            "end", self.get_description(_id, include_data=True)[0]
                        )
                        active_source_desc.pop(redis_channel)
                    elif data["type"] == FrameType.DATA.value:
                        _data[redis_channel] = {
                            "x": _data[redis_channel]["x"] + [data["data"]["x"]],
                            "y": _data[redis_channel]["y"] + [data["data"]["y"]],
                        }

                        self.emit(
                            "data", {"id": _id, "data": data["data"]},
                        )

                        self._append_data(
                            _id, data["data"], active_source_desc[redis_channel]
                        )
                    else:
                        msg = "Unknown frame type %s" % message
                        logging.getLogger("HWR").error(msg)
                except Exception:
                    msg = "Could not parse data in %s" % message
                    logging.getLogger("HWR").exception(msg)

    def _remove_available(self, _id):
        """
        Remove source with _id from list of avialable sources

        Args:
            _id (str): The id of the source to remove
        """
        sources = self._get_available()
        sources = {} if not sources else sources
        sources.pop(_id)

        self._r.set("HWR_DP_PUBLISHERS", json.dumps(sources))

    def _add_avilable(self, _id):
        """
        Add source with _id to list of avialable sources

        Args:
            _id (str): The id of the sources to remove
        """
        sources = self._get_available()
        sources = {} if not sources else sources
        sources[_id] = "HWR_DP_NEW_DATA_POINT_%s" % _id

        self._r.set("HWR_DP_PUBLISHERS", json.dumps(sources))

    def _get_available(self):
        """
        Returns:
            (dict): Where the key is the id of source and the value
                    the channel name to publish data to.
        """
        sources = self._r.get("HWR_DP_PUBLISHERS")
        sources = json.loads(sources) if sources else {}

        return sources

    def _set_description(self, _id, desc):
        """
        Sets the description of source with _id to desc

        Args:
            _id (str): The id of the source to remove
            desc (dict): "id": str,
                         "channel": str,
                         "name": str,
                         "data_type": str
                         "data_dim": float
                         "plot_type": str
                         "sample_rate": float
                         "content_type": str
                         "range": list (min, max)
                         "meta": str
                         "running": boolean,
        """
        self._r.set("HWR_DP_%s_DESCRIPTION" % _id, json.dumps(desc))

    def _get_description(self, _id):
        """
        Return the description of source with _id

        Returns:
            (dict): "id": str,
                     "channel": str,
                     "name": str,
                     "data_type": str
                     "data_dim": float
                     "plot_type": str
                     "sample_rate": float
                     "content_type": str
                     "range": list (min, max)
                     "meta": str
                     "running": boolean,
        """
        return json.loads(self._r.get("HWR_DP_%s_DESCRIPTION" % _id))

    def _update_description(self, _id, data):
        """
        Update the description of source with _id with data
        Args:
            _id (str): The id of the source to remove
            desc (dict): with key, value pairs to update
        """
        desc = self._get_description(_id)
        desc.update(data)
        self._set_description(_id, desc)

    def _append_data(self, _id, data, desc):
        """
        Append data to source with _id

        Args:
            _id (str): The id of the source to remove
            desc (dict): Publisher description
            data: x, y, (z) data to append
        """
        self._r.rpush("HWR_DP_%s_DATA_X" % _id, data.get("x", float("nan")))
        self._r.rpush("HWR_DP_%s_DATA_Y" % _id, data.get("y", float("nan")))

        if desc["data_dim"] > 1:
            self._r.rpush("HWR_DP_%s_DATA_Z" % _id, data.get("z", float("nan")))

    def _clear_data(self, _id):
        """
        Clear data of source with _id
        """
        desc = self._get_description(_id)

        self._r.delete("HWR_DP_%s_DATA_X" % _id)
        self._r.delete("HWR_DP_%s_DATA_Y" % _id)

        if desc["data_dim"] > 1:
            self._r.delete("HWR_DP_%s_DATA_Z" % _id)

    def _publish(self, _id, data):
        """
        Publish data to source with _id

        Args:
            _id (str): The id of the source to remove
            data: x, y, (z) data to append
        """
        self._r.publish("HWR_DP_NEW_DATA_POINT_%s" % _id, json.dumps(data))

    def register(
        self,
        _id,
        name,
        channel,
        axis_labels=["x", "y", "z"],
        data_type=DataType.FLOAT,
        data_dim=PlotDim.ONE_D,
        plot_type=PlotType.SCATTER,
        content_type="",
        sample_rate=0.5,
        _range=(None, None),
        meta={},
    ):

        plot_description = {
            "id": _id,
            "name": name,
            "axis_labels": axis_labels,
            "channel": channel,
            "data_type": data_type.value,
            "data_dim": data_dim.value,
            "plot_type": plot_type.value,
            "sample_rate": sample_rate,
            "content_type": content_type,
            "range": _range,
            "meta": meta,
            "running": False,
        }

        self._set_description(_id, plot_description)
        self._add_avilable(_id)

        return _id

    def pub(self, _id, data):
        self._publish(_id, {"type": FrameType.DATA.value, "data": data})

    def start(self, _id):
        self._publish(_id, {"type": FrameType.START.value, "data": {}})

    def stop(self, _id):
        self._update_description(_id, {"running": False})
        self._publish(_id, {"type": FrameType.STOP.value, "data": {}})

    def get_description(self, _id=None, include_data=False):
        desc = []

        if _id:
            _d = self._get_description(_id)

            if include_data:
                _d.update({"values": self.get_data(_id)})

            desc = [_d]

        else:
            available = self._get_available()

            for _id in available.keys():
                _d = self._get_description(_id)

            if include_data:
                _d.update({"values": self.get_data(_id)})

            desc.append(_d)

        return desc

    def get_data(self, _id):
        desc = self._get_description(_id)
        data = {
            "x": self._r.lrange("HWR_DP_%s_DATA_X" % _id, 0, -1),
            "y": self._r.lrange("HWR_DP_%s_DATA_Y" % _id, 0, -1),
        }

        if desc["data_dim"] > 1:
            data.update(
                {"z": self._r.lrange("HWR_DP_%s_DATA_Z" % _id, 0, -1),}
            )

        return data
