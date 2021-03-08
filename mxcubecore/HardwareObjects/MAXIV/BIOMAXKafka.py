"""
A client for Biomax Kafka services.
"""
import logging
import time
import json
import uuid
import re
import requests
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR


class BIOMAXKafka(HardwareObject):
    """
    Web-service client for Kafka services.
    Example xml file:
    <object class="MAXIV.BiomaxKafka">
      <kafka_server>my_host.maxiv.lu.se</kafka_server>
      <topic>biomax</topic>
      <object href="/session" role="session"/>
    </object>
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.kafka_server = None
        self.topic = ""

    def init(self):
        """
        Init method declared by HardwareObject.
        """
        self.kafka_server = self.get_property("kafka_server")
        self.topic = self.get_property("topic")
        self.beamline_name = HWR.beamline.session.beamline_name
        self.file = open("/tmp/kafka_errors.txt", "a")
        self.url = self.kafka_server + "/kafka"

        logging.getLogger("HWR").info("KAFKA link initialized.")

    def key_is_snake_case(sel, k):
        return "_" in k

    def snake_to_camel(self, text):
        return re.sub("_([a-zA-Z0-9])", lambda m: m.group(1).upper(), text)

    def send_data_collection(self, collection_data):
        d = dict()

        d.update(
            {
                "uuid": str(uuid.uuid4()),
                "beamline": self.beamline_name,
                "proposal": HWR.beamline.session.get_proposal(),  # e.g. MX20170251
                "session": HWR.beamline.session.get_session_start_date(),  # 20171206
                "userCategory": "visitors",  # HWR.beamline.session.get_user_category()  #staff or visitors
                "_v": "0",
            }
        )

        collection_data.update(d)

        for k in collection_data.keys():
            if self.key_is_snake_case(k):
                collection_data[self.snake_to_camel(k)] = collection_data.pop(k)

        data = json.dumps(collection_data)

        try:
            requests.post(self.url, data=data)
            logging.getLogger("HWR").info(
                "Pushed data collection info to KAFKA, UUID: %s"
                % collection_data["uuid"]
            )
        except Exception as ex:
            self.file.write(time.strftime("%d %b %Y %H:%M:%S", time.gmtime()) + "\n")
            self.file.write(data + "\n")
            self.file.write(50 * "#" + "\n")
            self.file.flush()
            logging.getLogger("HWR").error(
                "KAFKA link error. %s; data saved to /tmp/kafka_errors.txt" % str(ex)
            )
