import os
import subprocess
import errno
import time
import select
import fcntl

PIPE = subprocess.PIPE


class Popen(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        subprocess.Popen.__init__(self, *args, **kwargs)

    def recv(self, maxsize=None):
        return self._recv("stdout", maxsize)

    def recv_err(self, maxsize=None):
        return self._recv("stderr", maxsize)

    def send_recv(self, input="", maxsize=None):
        return self.send(input), self.recv(maxsize), self.recv_err(maxsize)

    def get_conn_maxsize(self, which, maxsize):
        if maxsize is None:
            maxsize = 1024
        elif maxsize < 1:
            maxsize = 1
        return getattr(self, which), maxsize

    def _close(self, which):
        getattr(self, which).close()
        setattr(self, which, None)

    def send(self, input):
        if not self.stdin:
            return None

        if not select.select([], [self.stdin], [], 0)[1]:
            return 0

        try:
            written = os.write(self.stdin.fileno(), input)
        except OSError as why:
            if why[0] == errno.EPIPE:  # broken pipe
                return self._close("stdin")
            raise

        return written

    def _recv(self, which, maxsize):
        conn, maxsize = self.get_conn_maxsize(which, maxsize)
        if conn is None:
            return None

        flags = fcntl.fcntl(conn, fcntl.F_GETFL)
        if not conn.closed:
            fcntl.fcntl(conn, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        try:
            if not select.select([conn], [], [], 0)[0]:
                return ""

            r = conn.read(maxsize)
            if not r:
                return self._close(which)

            if getattr(self, "universal_newlines"):
                r = getattr(self, "_translate_newlines")(r)
            return r
        finally:
            if not conn.closed:
                fcntl.fcntl(conn, fcntl.F_SETFL, flags)


def recv_some(p, t=0.1, e=1, tr=5, stderr=0):
    if tr < 1:
        tr = 1
    x = time.time() + t
    y = []
    r = ""
    pr = p.recv
    if stderr:
        pr = p.recv_err
    while time.time() < x or r:
        r = pr()
        if r is None:
            if e:
                raise Exception("Other end disconnected")
            else:
                break
        elif r:
            y.append(r)
        else:
            time.sleep(max((x - time.time()) / tr, 0))
    return "".join(y)


def send_all(p, data):
    while len(data):
        sent = p.send(data)
        if sent is None:
            raise Exception("Other end disconnected")
        data = buffer(data, sent)
