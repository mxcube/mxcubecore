"""
Secure XML RPC request handler for workflow execution based on tokens.
Inspired from this code:
http://code.activestate.com/recipes/496786-simple-xml-rpc-server-over-https
"""

import sys

if sys.version_info > (3, 0):
    from xmlrpc.server import SimpleXMLRPCRequestHandler
else:
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler


__author__ = "Olof Svensson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["MxCuBE collaboration"]

__version__ = ""
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Draft"


class SecureXMLRpcRequestHandler(SimpleXMLRPCRequestHandler):
    """
    Secure XML-RPC request handler class.

    It it very similar to SimpleXMLRPCRequestHandler but it checks for a
    "Token" entry in the header. If this token doesn't correspond to a
    reference token the server sends a "401" (Unauthorized) reply.
    """

    __referenceToken = None

    @staticmethod
    def setReferenceToken(token):
        SecureXMLRpcRequestHandler.__referenceToken = token

    def setup(self):
        self.connection = self.request
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.wfile = self.connection.makefile('wb', self.wbufsize)

    def do_POST(self):
        """
        Handles the HTTPS POST request.

        It was copied out from SimpleXMLRPCServer.py and modified to check for "Token" in the headers.
        """
        # Check that the path is legal
        if not self.is_rpc_path_valid():
            self.report_404()
            return

        referenceToken = SecureXMLRpcRequestHandler.__referenceToken
        if (
            referenceToken is not None
            and "Token" in self.headers
            and referenceToken == self.headers["Token"]
        ):
            try:
                # Get arguments by reading body of request.
                # We read this in chunks to avoid straining
                # socket.read(); around the 10 or 15Mb mark, some platforms
                # begin to have problems (bug #792570).
                max_chunk_size = 10 * 1024 * 1024
                size_remaining = int(self.headers["content-length"])
                L = []
                while size_remaining:
                    chunk_size = min(size_remaining, max_chunk_size)
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                    L.append(chunk.decode('utf-8'))
                    size_remaining -= len(L[-1])
                data = "".join(L)
                # In previous versions of SimpleXMLRPCServer, _dispatch
                # could be overridden in this class, instead of in
                # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
                # check to see if a subclass implements _dispatch and dispatch
                # using that method if present.
                response = self.server._marshaled_dispatch(
                    data, getattr(self, "_dispatch", None)
                )
            except Exception as e:  # This should only happen if the module is buggy
                # internal error, report as HTTP server error
                self.send_response(500)

                # Send information about the exception if requested
                if (
                    hasattr(self.server, "_send_traceback_header")
                    and self.server._send_traceback_header
                ):
                    self.send_header("X-exception", str(e))
                    self.send_header("X-traceback", traceback.format_exc())

                self.end_headers()
            else:
                # got a valid XML RPC response
                self.send_response(200)
                self.send_header("Content-type", "text/xml")
                self.send_header("Content-length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

                # shut down the connection
                self.wfile.flush()
                self.connection.shutdown(1)
        else:
            # Unrecognized token - access unauthorized
            self.send_response(401)
            self.end_headers()

