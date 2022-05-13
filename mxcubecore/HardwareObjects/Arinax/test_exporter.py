import time

import gevent.event
import sys

sys.path.append('/home/arinax/mxcube/mxcube3')
from exporter import ExporterClient
from exporter.StandardClient import PROTOCOL
from gevent.monkey import patch_all
patch_all()

# from Exporter import Exporter
# import Tango


address = '10.30.51.151'
port = 9002
timeout = 3
retries = 1

client = ExporterClient.ExporterClient(address, port, PROTOCOL, timeout, retries)

def task1():
    print("task1 started")
    client = ExporterClient.ExporterClient(address,port, PROTOCOL.STREAM, timeout, retries)
    time.sleep(0.1)
    client.read_property("State")
    print(client.get_method_list())
    print(client.get_property_list())

    print("task1 finished")
    # client.write_property("OmegaPosition",300,timeout=5)

def wait_ready():
    while(client.read_property("State") != "Ready"):
        print(".", end="")
        gevent.sleep(0.1)
    print("", end="\n")

def omega_scan():
    # Omega Scan:
    print("Doing Omega Scan ")
    frame_number = 100
    start_angle = 143.090
    scan_range = 5.0
    exposure_time = 0.200
    number_of_passes = 1
    parameters = (frame_number, start_angle, scan_range, exposure_time, number_of_passes,)
    client.execute_async("startScanEx", parameters)
    wait_ready()
    print("Omega Scan finished")


def multi_axis_scan():
    # client = ExporterClient.ExporterClient(address, port, PROTOCOL, timeout, retries)
    # 4D Scan:
    print("Doing 4D Scan")
    start_angle = 140
    scan_range = 5
    exposure_time = 1
    start_y = 0
    start_z = 0
    start_cx = 0
    start_c = 0
    stop_y = 0.100
    stop_z = 0
    stop_cx = 0
    stop_cy = 0
    parameters = (start_angle, scan_range, exposure_time, start_y, start_z, start_cx, start_c, stop_y,
                  stop_z, stop_cx, stop_cy,)
    client.execute("startScan4DEx", parameters)
    wait_ready()
    print("4D Scan finished")


def raster_scan():
    # client = ExporterClient.ExporterClient(address, port, PROTOCOL, timeout, retries)
    # Raster Scan:
    print("Doing Raster Scan")
    omega_range = 5
    line_range = 0.100
    total_uturn_range = 0.100
    start_omega = 143.09
    start_y = 0
    start_z = 0
    start_cx = 0
    start_cy = 0
    number_of_lines = 10
    frames_per_lines = 10
    exposure_time = 1  # time in s
    invert_direction = False
    use_centring_table = False
    shutterless = False
    parameters = (omega_range, line_range, total_uturn_range, start_omega, start_y,
                  start_z, start_cx, start_cy, number_of_lines, frames_per_lines, exposure_time,
                  invert_direction, use_centring_table, shutterless,)
    client.execute("startRasterScanEx", parameters)
    wait_ready()
    print("Raster Scan finished")


t1 = gevent.spawn(omega_scan)
gevent.joinall([t1])

# omega_scan()
#multi_axis_scan()
# raster_scan()