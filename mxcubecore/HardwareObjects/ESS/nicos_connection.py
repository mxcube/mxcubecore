import copy
import time

from nicos.clients.base import (
    ConnectionData,
    NicosClient,
)
from nicos.protocols.daemon import (
    STATUS_IDLE,
    STATUS_IDLEEXC,
)
from nicos.utils.loggers import (
    ACTION,
    INPUT,
)

EVENTMASK = ("watch", "datapoint", "datacurve", "clientexec")


class NICOSConnection(NicosClient):
    """NICOSConnection Class

    NICOSConnection class is based on the ones at
    nicos/clients/ipython/nicos.py, but with the IPython layer dependency
    removed. This way, NICOS commands can be called more directly.

    Also, unused commands were removed, and some were added
    (get_dev_param_value(), get_status()).
    """

    livedata = {}
    status = "idle"

    def __init__(self):
        self.message_queue = []
        super().__init__(self.log)

    def log(self, name, txt):
        self.message_queue.append((name, txt))

    def print_queue(self):
        """For debugging."""
        for msg in self.message_queue:
            print(msg[1])
        self.message_queue = []

    def signal(self, name, data=None, exc=None):
        """Has to be implemented."""
        accept = ["message", "processing", "done"]
        if name in accept:
            self.log_func(name, data)
        elif name == "livedata":
            converted_data = []
            for desc, ardata in zip(data["datadescs"], exc):
                npdata = np.frombuffer(ardata, dtype=desc["dtype"])
                npdata = npdata.reshape(desc["shape"])
                converted_data.append(npdata)
            self.livedata[data["det"] + "_live"] = converted_data
        elif name == "status":
            status, _ = data
            if status == STATUS_IDLE or status == STATUS_IDLEEXC:
                self.status = "idle"
            else:
                self.status = "run"
        else:
            if name != "cache":
                pass

    def _do_command(self, line):
        com = "%s" % line.strip()
        if self.status == "idle":
            self.run(com)
            return com
        return None

    def _do_connect(self, conndata, eventmask=None):
        NicosClient.connect(self, conndata, eventmask)

    def start_connection(self, line):
        """Try to connect to NICOS."""
        data = line.split()
        if len(data) < 5:
            print("Not enough data to connect, need host port user password")
            return
        con = ConnectionData(data[1], data[2], data[3], data[4])
        self._do_connect(con, eventmask=EVENTMASK)

    def is_connected(self):
        return self.isconnected

    def get_status(self):
        return self.status

    def process_command(self, line):
        """Process a NICOS command line and return the result."""
        start_detected = False
        ignore = [ACTION, INPUT]
        reqID = None
        testcom = self._do_command(line)
        if not testcom:
            return "NICOS is busy, cannot send commands"
        output_msg = None
        while True:
            time.sleep(1)
            if self.message_queue:
                # Own copy for thread safety
                work_queue = copy.deepcopy(self.message_queue)
                self.message_queue = []
                for name, message in work_queue:
                    # print('name, message = {}, {}'.format(name, message)) # debug messages
                    if name == "processing":
                        if message["script"] == testcom:
                            start_detected = True
                            reqID = message["reqid"]
                        continue
                    if name == "done" and message["reqid"] == reqID:
                        return output_msg
                    if type(message) == list:
                        if message[2] in ignore:
                            continue
                        if message[0] != "nicos":
                            messagetxt = message[0] + " " + message[3]
                        else:
                            messagetxt = message[3]
                    if start_detected and reqID == message[-1]:
                        # Capturing the output message here for the NICOS commands
                        # we need (e.g., get_status()).
                        if "status" in line:
                            output_msg = messagetxt

    def get_dev_param_value(self, dev_name, param_name="value"):
        """Return the value of a device parameter. The default parameter
        name is 'value'."""
        par = dev_name + "." + param_name
        # Check for livedata first
        if par in self.livedata:
            return self.livedata[par]

        # Now check for scan data
        if par == "scandata":
            xs, ys, _, names = self.eval(
                '__import__("nicos").commands.analyze._getData()[:4]'
            )
            return xs, ys, names

        # Try get device data from NICOS
        if par.find(".") > 0:
            devpar = par.split(".")
            return self.getDeviceParam(devpar[0], devpar[1])
        else:
            return self.getDeviceValue(par)

    def end_connection(self):
        self.disconnect()


def connect_to_nicos(host, port, user, password):
    """Returns a connection to NICOS."""
    line = "/connect {} {} {} {}".format(host, port, user, password)
    nicos_conn = NICOSConnection()
    nicos_conn.start_connection(line)
    return nicos_conn
