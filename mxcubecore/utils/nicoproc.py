import logging
import xmlrpc.client

USE_NICOPROC = False
HOST = "http://localhost:9998/"

def start(dc_paramters, file_paramters):
    print("NICO-DEBUG:")
    print(dc_paramters)
    param = {
        "exposure":dc_paramters['oscillation_sequence'][0]["exposure_time"],
        "detector_distance":dc_paramters["detectorDistance"],
        "wavelength":dc_paramters["wavelength"],
        "orgx":dc_paramters["xBeam"],
        "orgy":dc_paramters["yBeam"],
        "oscillation_range":dc_paramters['oscillation_sequence'][0]["range"],
        "start_angle":dc_paramters['oscillation_sequence'][0]["start"],
        "number_images":dc_paramters['oscillation_sequence'][0]["number_of_images"],
        "image_first":dc_paramters['oscillation_sequence'][0]["start_image_number"],
        "fileinfo":file_paramters
    }

    logging.getLogger("HWR").info("NICOPROC START")

    with xmlrpc.client.ServerProxy(HOST) as p:
        p.start(param)

def stop():
    logging.getLogger("HWR").info("NICOPROC STOP")
    
    with xmlrpc.client.ServerProxy(HOST) as p:
        p.stop()
    
    
