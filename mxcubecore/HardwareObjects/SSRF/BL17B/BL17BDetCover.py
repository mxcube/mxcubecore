import socket
import binascii
import time

class DetCover(object):

    def __init__(self):
        pass

    # DO1:0064
    def closeDetCover(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = "10.30.63.118"
        port = 502
        server.connect((host, port))
        modbus_data = '000100000006FF0500640000'
        # binascii Send hexadecimal
        send_data = binascii.a2b_hex(modbus_data)
        server.sendall(send_data)
        time.sleep(0.5)
        server.close()
        #pass


    def openDetCover(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = "10.30.63.118"
        port = 502
        server.connect((host, port))
        modbus_data = '000100000006FF050064FF00'
        # binascii Send hexadecimal
        send_data = binascii.a2b_hex(modbus_data)
        server.sendall(send_data)
        time.sleep(0.5)
        server.close()
        #pass

if __name__ == "__main__":
   detCover = DetCover()
   detCover.onDetCover()
   #detCover.offDetCover()