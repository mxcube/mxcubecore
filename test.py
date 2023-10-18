from suds.transport.http import HttpAuthenticated
from suds.client import Client

t1 = HttpAuthenticated(
    username='zhangsan',
    password='zhangsan',
    proxy={}
)
_shipping = Client(
    'http://10.30.61.230/ispyb/ispyb-ws/ispybWS/ToolsForShippingWebService?wsdl',
    timeout=3,
    transport=t1,
    cache=None,
    proxy={},
)
print(_shipping)