from HardwareRepository.BaseHardwareObjects import HardwareObject
import os
import sys
from bliss.config import static
from bliss.data.node import DataNodeIterator, _get_or_create_node
import gevent
import itertools
import numpy

def all_equal(iterable):
    g = itertools.groupby(iterable)
    return next(g, True) and not next(g, False)

def watch_data(scan_node, scan_new_callback, scan_data_callback, scan_end_callback):
    scan_info = scan_node._info.get_all()
    if scan_info['type'] == 'ct':
        return

    timescan = scan_info["type"] == "timescan"
    if not timescan:
      del scan_info["motors"][0]
    scan_info["labels"] = scan_info["motors"] + scan_info["counters"]
    ndata = len(scan_info["labels"])
    del scan_info["motors"]
    del scan_info["counters"]
    scan_data = dict()
    data_indexes = dict()
    
    scan_new_callback(scan_info)

    scan_data_iterator = DataNodeIterator(scan_node)
    for event_type, event_data in scan_data_iterator.walk_events(filter="zerod"):
        if event_type is scan_data_iterator.NEW_DATA_IN_CHANNEL_EVENT:
            zerod, channel_name = event_data
            if not timescan and channel_name == "timestamp":
                continue
            data_channel = zerod.get_channel(channel_name)
            data = data_channel.get(data_indexes.setdefault(channel_name, 0), -1)
            data_indexes[channel_name] += len(data)
            scan_data.setdefault(channel_name, []).extend(data)
            if len(scan_data) == ndata and all_equal(data_indexes.itervalues()):
                scan_data_callback(scan_info, scan_data)
                if data_indexes[channel_name] == scan_info["npoints"]:
                    scan_end_callback(scan_info)
                scan_data = dict()

def watch_session(session_name, scan_new_callback, scan_data_callback, scan_end_callback):
    session_node = _get_or_create_node(session_name, node_type='session')
    if session_node is not None:
        data_iterator = DataNodeIterator(session_node)

        watch_data_task = None
        last = True
        for scan_node in data_iterator.walk_from_last(filter='scan'):
            if last:
                # skip the last one, we are interested in new ones only
                last = False
                continue
            if watch_data_task:
                watch_data_task.kill()
            watch_data_task = gevent.spawn(watch_data, scan_node, scan_new_callback, scan_data_callback, scan_end_callback)

class Bliss(HardwareObject):
  def __init__(self, *args):
    HardwareObject.__init__(self, *args)

  def init(self, *args):
     cfg = static.get_config()
     session = cfg.get(self.getProperty("session"))

     session.setup(self.__dict__, verbose=True)

     self.__session_watcher = gevent.spawn(watch_session, self.getProperty("session"), self.__on_scan_new, self.__on_scan_data, self.__on_scan_end)
     self.__scan_data = dict()

  def __on_scan_new(self, scan_info):
      scan_id = scan_info["scan_nb"]
      self.__scan_data[scan_id] = list()

      if not scan_info['save']:
          scan_info['root_path'] = '<no file>'
   
      self.emit("new_plot", { "id": scan_info["scan_nb"],
                              "title": scan_info["title"], 
                              "labels": scan_info["labels"] })

  def __on_scan_data(self, scan_info, data):
      scan_id = scan_info["scan_nb"]
      new_data = numpy.column_stack([data[name] for name in scan_info["labels"]])
      self.__scan_data[scan_id].append(new_data)
      self.emit("plot_data", { "id": scan_id, "data": new_data.tolist() })

  def __on_scan_end(self, scan_info):
      scan_id = scan_info["scan_nb"]
      self.emit("plot_end", { "id": scan_id, "data": numpy.concatenate(self.__scan_data[scan_id]).tolist() })
      del self.__scan_data[scan_id]

