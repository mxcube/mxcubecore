"""
A client for Biomax Kafka services.
"""
import logging
import gevent
import os
import time
import json
import uuid
import re

from kafka import KafkaConsumer, KafkaProducer


from HardwareRepository.BaseHardwareObjects import HardwareObject
from datetime import datetime


class BiomaxKafka(HardwareObject):
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
        self.session_hwobj = None
        self.topicsna    = ''

    def init(self):
        """
        Init method declared by HardwareObject.
        """
        self.kafka_server = self.getProperty('kafka_server')
        self.topic = self.getProperty('topic')
        self.session_hwobj = self.getObjectByRole('session')
        self.beamline_name = self.session_hwobj.beamline_name

        self.producer = KafkaProducer(bootstrap_servers=self.kafka_server)
        
        logging.getLogger("HWR").info('KAFKA link initialized.')

    def key_is_snake_case(sel, k):
        return '_' in k

    def snake_to_camel(self, text):
        return re.sub('_([a-zA-Z0-9])', lambda m: m.group(1).upper(), text)
    
    # def convert(self, name):
    #     s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    #     return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def send_data_collection(self, collection_data):
        d = dict()

        d.update('uuid': str(uuid.uuid4()),
                 'beamline': self.beamline_name,
                 'proposal': self.session_hwobj.get_proposal(),  # e.g. MX20170251
                 'session': self.session_hwobj.get_session_start_date(),  # 20171206
                 'userCategory': self.session_hwobj.get_user_category()  #staff or visitors
                )

        collection_data.update(d)

        for k in collection_data.keys():
            if self.key_is_snake_case(k):
                collection_data[self.snake_to_camel(k)] = collection_data.pop(k)
        try:
            producer.send(self.topic, json.dumps(collection_data))
        except Exception as ex:
            logging.getLogger("HWR").error('KAFKA link error. %s' % str(ex))

