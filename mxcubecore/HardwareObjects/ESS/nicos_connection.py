from nicos.clients.base import (
    ConnectionData,
    NicosClient,
)

EVENTMASK = ("livedata", "watch", "dataset", "datacurve", "datapoint", "clientexec")


class NICOSConnection(NicosClient):
    """NICOSConnection Class

    Basic commands to connect and communicate with a NICOS server.
    """

    def __init__(self):
        self.message_queue = []
        super().__init__(self.log)

    def log(self, txt):
        self.message_queue.append((txt))

    def signal(self, name, data=None, exc=None):
        """Has to be implemented."""
        pass

    def connect(self, host, port, user, password):
        """Try to connect to NICOS server."""
        conndata = ConnectionData(host, port, user, password)
        super().connect(conndata, EVENTMASK)

    def is_connected(self):
        return self.isconnected

    def get_dev_value(self, dev_name):
        """Return the current value of a device.
        This invokes <dev_name>.read() at NICOS server."""
        return self.getDeviceValue(dev_name)

    def disconnect(self):
        """Disconnect from NICOS server."""
        super().disconnect()

    def run_command(self, command_line):
        """Execute a NICOS command line."""
        return self.run(command_line)

    def get_dev_status(self, dev_name):
        """Return the status of a device.
        This invokes <dev_name>.status() at NICOS server.

        The returned tuple is: (STATUS_CODE, status_text).
        See nicos/core/status.py for the meaning of the status codes."""
        line = f"{dev_name}.status()"
        return self.eval(line)


def get_nicos_connected(host, port, user, password="any"):
    """Returns a connected NICOS object."""
    if password is None or len(password) == 0:
        raise Exception("Error: a non-empty password should be set.")
    nicos_conn = NICOSConnection()
    nicos_conn.connect(host, port, user, password)
    return nicos_conn
