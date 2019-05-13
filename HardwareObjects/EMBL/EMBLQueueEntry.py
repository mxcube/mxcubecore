import logging

from HardwareRepository.dispatcher import dispatcher
from HardwareRepository.HardwareObjects.base_queue_entry import BaseQueueEntry, QueueExecutionException, QUEUE_ENTRY_STATUS

class XrayImagingQueueEntry(BaseQueueEntry):

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)

    def execute(self):
        BaseQueueEntry.execute(self)
        self.beamline_setup.xray_imaging_hwobj.execute(self.get_data_model())

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

        queue_controller = self.get_queue_controller()
        queue_controller.connect(self.beamline_setup.xray_imaging_hwobj, "collectImageTaken", self.image_taken)
        queue_controller.connect(self.beamline_setup.xray_imaging_hwobj, "collectFailed", self.collect_failed)

        self.beamline_setup.xray_imaging_hwobj.pre_execute(self.get_data_model())

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        self.beamline_setup.xray_imaging_hwobj.post_execute(self.get_data_model())

        queue_controller = self.get_queue_controller()
        queue_controller.disconnect(self.beamline_setup.xray_imaging_hwobj, "collectImageTaken", self.image_taken)
        queue_controller.disconnect(self.beamline_setup.xray_imaging_hwobj, "collectFailed", self.collect_failed)

    def stop(self):
        BaseQueueEntry.stop(self)
        self.beamline_setup.xray_imaging_hwobj.stop_collect()

    def collect_failed(self, message):
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        self.get_view().setText(1, "Failed")
        self.status = QUEUE_ENTRY_STATUS.FAILED
        logging.getLogger("queue_exec").error(message.replace("\n", " "))
        raise QueueExecutionException(message.replace("\n", " "), self)

    def image_taken(self, image_number):
        if image_number > 0:
            num_images = (
                self.get_data_model().acquisition.acquisition_parameters.num_images
            )
            self.get_view().setText(1, str(image_number) + "/" + str(num_images))
