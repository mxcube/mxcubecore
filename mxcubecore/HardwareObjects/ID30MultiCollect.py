from ESRFMultiCollect import *

class ID30MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, CcdDetector(), FixedEnergy(0.965, 12.8))

    @task
    def data_collection_hook(self, data_collect_parameters):
        self.getChannelObject("parameters").setValue(data_collect_parameters)
        self.execute_command("build_collect_seq")

    @task
    def move_detector(self, detector_distance):
        pass #self.bl_control.resolution.newDistance(detector_distance)

    @task
    def set_resolution(self, new_resolution):
        pass #self.bl_control.resolution.move(new_resolution)

    def get_detector_distance(self):
        return 260 #self.bl_control.resolution.res2dist(self.bl_control.resolution.getPosition()

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if osc_range < 1E-4:
            # still image
            return (start, start+osc_range)
        else:
            return (start, start+osc_range)
        
    @task
    def do_oscillation(self, start, end, exptime, npass):
        pass

    def get_flux(self):
        return -1

    def set_transmission(self, transmission_percent):
    	pass

    def get_transmission(self):
        return 100



