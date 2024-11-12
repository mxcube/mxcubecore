import gevent
import numpy

from mxcubecore.BaseHardwareObjects import HardwareObject


def plot_emitter(new_plot, plot_data, plot_end):
    scan_nb = 0
    data = numpy.random.normal(0, 1, 30)  # 30 points
    info = {
        "scan_nb": scan_nb,
        "title": "Test data %d" % scan_nb,
        "labels": ["angle", "diode value"],
    }

    while True:
        gevent.sleep(10)

        scan_nb += 1
        info["scan_nb"] = scan_nb
        new_plot(info)

        for i in range(30):
            plot_data(info, {"angle": i, "diode value": data[i]})
            gevent.sleep(0.1)

        plot_end(info)


class PlottingMockup(HardwareObject):
    # this emits plot data for 3 seconds, every 10 seconds

    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self, *args):
        self.__plotter = gevent.spawn(
            plot_emitter, self.__on_scan_new, self.__on_scan_data, self.__on_scan_end
        )
        self.__scan_data = dict()

    def __on_scan_new(self, scan_info):
        scan_id = scan_info["scan_nb"]
        self.__scan_data[scan_id] = list()

        self.emit(
            "new_plot",
            {
                "id": scan_info["scan_nb"],
                "title": scan_info["title"],
                "labels": scan_info["labels"],
            },
        )

    def __on_scan_data(self, scan_info, data):
        scan_id = scan_info["scan_nb"]
        new_data = numpy.column_stack([data[name] for name in scan_info["labels"]])
        self.__scan_data[scan_id].append(new_data)
        self.emit(
            "plot_data",
            {
                "id": scan_id,
                "data": numpy.concatenate(self.__scan_data[scan_id]).tolist(),
            },
        )

    def __on_scan_end(self, scan_info):
        scan_id = scan_info["scan_nb"]
        self.emit(
            "plot_end",
            {
                "id": scan_id,
                "data": numpy.concatenate(self.__scan_data[scan_id]).tolist(),
            },
        )
        del self.__scan_data[scan_id]
