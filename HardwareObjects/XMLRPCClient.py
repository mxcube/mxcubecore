from HardwareRepository.BaseHardwareObjects import HardwareObject


try:
    from xmlrpclib import ServerProxy
except:
    from xmlrpc.client import ServerProxy

class XMLRPCClient(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.host = None
        self.port = None
        self.all_interfaces = None
        self.server_proxy = None

    def init(self):
        self.open()

    def close(self):
        pass

    def open(self):
        server_url = "http://localhost:9090"
        self.server_proxy = ServerProxy(server_url)

    def test(self, msg):
        dict_dialog = {"payload": msg}
        self.server_proxy.test_method(dict_dialog)
