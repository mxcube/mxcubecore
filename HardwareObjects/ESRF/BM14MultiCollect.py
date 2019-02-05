import os
import socket
import gevent
import logging

from HardwareRepository.TaskUtils import task
from ESRFMultiCollect import CcdDetector, ESRFMultiCollect, TunableEnergy
from detectors.TacoMarDetector import Mar225


class BM14MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, CcdDetector(Mar225), TunableEnergy())
        self._notify_greenlet = None

    @task
    def data_collection_hook(self, data_collect_parameters):
        self.getChannelObject("parameters").setValue(data_collect_parameters)
        self.execute_command("build_collect_seq")
        self.execute_command("prepare_beamline")

    @task
    def move_detector(self, detector_distance):
        self.bl_control.resolution.newDistance(detector_distance)

    @task
    def set_resolution(self, new_resolution):
        self.bl_control.resolution.move(new_resolution)

    def get_detector_distance(self):
        return self.bl_control.resolution.res2dist(
            self.bl_control.resolution.getPosition()
        )

    def get_undulators_gaps(self):
        return []

    def generate_image_jpeg(self, *args, **kwargs):
        return

    def get_flux(self):
        return 0

    @task
    def set_detector_filenames(
        self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
    ):
        self.last_image_filename = filename
        return ESRFMultiCollect.set_detector_filenames(
            self,
            frame_number,
            start,
            filename,
            jpeg_full_path,
            jpeg_thumbnail_full_path,
        )

    def adxv_notify(self, image_filename):
        logging.info("adxv_notify %r", image_filename)
        # image_filename="/data/bm14/inhouse/opd14/20150908/RAW_DATA/adxvtest/opd14adxv3_1_0004.mccd"
        try:
            # do a 'stat' to force NFS cache clearing
            os.stat(os.path.dirname(image_filename))
            os.system("ls " + image_filename)
            if not os.path.isfile(image_filename):
                logging.info("No image file '%s` on disk (yet)", image_filename)
            else:
                adxv_notify_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                adxv_notify_socket.connect(("cakenew.esrf.fr", 8100))
                adxv_notify_socket.sendall("load_image %s\n" % image_filename)
                adxv_notify_socket.close()
        except Exception:
            logging.info("adxv_notify exception : %r", image_filename)
            # print Exception, err

    @task
    def write_image(self, last_frame):
        ESRFMultiCollect.write_image(self, last_frame)
        if last_frame:
            gevent.spawn_later(1, self.adxv_notify, self.last_image_filename)
        else:
            if self._notify_greenlet is None or self._notify_greenlet.ready():
                self._notify_greenlet = gevent.spawn_later(
                    1, self.adxv_notify, self.last_image_filename
                )
