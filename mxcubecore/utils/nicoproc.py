import logging
import xmlrpc.client

USE_NICOPROC = False
HOST = "http://lid29control-2:9998"

def start(dc_paramters, file_paramters):
    print("NICO-DEBUG:")
    print(dc_paramters)
    param = {
        "exposure": dc_paramters["oscillation_sequence"][0]["exposure_time"],
        "detector_distance": dc_paramters["detectorDistance"],
        "wavelength": dc_paramters["wavelength"],
        "orgx": dc_paramters["xBeam"],
        "orgy": dc_paramters["yBeam"],
        "oscillation_range": dc_paramters["oscillation_sequence"][0]["range"],
        "start_angle": dc_paramters["oscillation_sequence"][0]["start"],
        "number_images": dc_paramters["oscillation_sequence"][0]["number_of_images"],
        "image_first": dc_paramters["oscillation_sequence"][0]["start_image_number"],
        "fileinfo": file_paramters,
    }

    logging.getLogger("HWR").info("NICOPROC START")

    with xmlrpc.client.ServerProxy(HOST) as p:
        p.start(param)


def start_ssx(beamline_values, params, path, experiment_type=""):
    param = {
        "exposure": params.user_collection_parameters.exp_time,
        "detector_distance": beamline_values.detector_distance,
        "wavelength": beamline_values.wavelength,
        "orgx": beamline_values.beam_x,
        "orgy": beamline_values.beam_y,
        "oscillation_range": params.collection_parameters.osc_range,
        "start_angle": params.collection_parameters.osc_start,
        "number_images": params.user_collection_parameters.num_images,
        "image_first": params.collection_parameters.first_image,
        "fileinfo": params.path_parameters.dict(),
        "root_path": path,
        "experiment_type": experiment_type,
    }

    logging.getLogger("HWR").info("NICOPROC START")

    try:
        with xmlrpc.client.ServerProxy(HOST) as p:
            p.start(param)
    except Exception:
        logging.getLogger("HWR").exception("")

def stop():
    logging.getLogger("HWR").info("NICOPROC STOP")

    with xmlrpc.client.ServerProxy(HOST) as p:
        p.stop()
