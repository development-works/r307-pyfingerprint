# create an interface to communicate with sensor via my pc
from serial import Serial
import time

HEADER = bytes.fromhex('EF01')

PID_COMMAND = bytes.fromhex('01')
PID_ACK = bytes.fromhex('07')
PID_DATA = bytes.fromhex('02')
PID_EOD = bytes.fromhex('08')

IC_VERIFY_PASSWORD = bytes.fromhex('13')
IC_GENERATE_IMAGE = bytes.fromhex('01')
IC_DOWNLOAD_IMAGE = bytes.fromhex('0a')

CC_SUCCESS = bytes.fromhex('00')
CC_ERROR = bytes.fromhex('01')
CC_WRONG_PASS = bytes.fromhex('13')
CC_FINGER_NOT_DETECTED = bytes.fromhex('02')
CC_FAILED_TO_COLLECT_FINGER = bytes.fromhex('03')

# download char buffer
# download image
# generate image
class Sensor:
    def __init__(self, port, baudrate):
        self._serial = Serial(port, baudrate=baudrate, timeout=3)
        self._password = bytes.fromhex('00000000')
        self._address = bytes.fromhex('FFFFFFFF')

        self.verify_password()

    # 0000 0000 0000 0111
    #              0    7
    # packet length = length of packet content + length of checksum
    # for data length we need to send the number of bytes(like here we have
    # 7byte of total data and checksum so we need to send "7" as input)

    def checksum(self, pid, package_len, content):
        checksum = int.from_bytes(pid, byteorder='big') + package_len

        # Addition of individual bytes in content as otherwise int conversion
        # will not make sense
        for byte in content:
            checksum = checksum + byte

        checksum = checksum & 0xFFFF

        ''' 0xFFFF - to remove exception in case checksum is greater than 2 
        bytes
             1111 1111 1111 1111
        0001 0011 0011 1011 1001 - Checksum
             0011 0011 1011 1001 - result
        '''

        return checksum.to_bytes(2, byteorder='big')

    def send_packet(self, pid, package_len, content):
        checksum = self.checksum(pid, package_len, content)
        # Getting value of checksum

        self._serial.write(HEADER)
        self._serial.write(self._address)
        self._serial.write(pid)
        self._serial.write(package_len.to_bytes(2,byteorder='big'))
        self._serial.write(content)
        self._serial.write(checksum)

    def recieve_packet(self):
        header_rcv = self._serial.read(2)
        if header_rcv != HEADER:
            raise Exception("Acknowledgment Header invalid")

        address_rcv = self._serial.read(4)
        if address_rcv != self._address:
            raise Exception("Address is invalid")

        pid_rcv = self._serial.read(1)
        if pid_rcv != PID_ACK:
            raise Exception("PID is invalid")

        len_rcv = self._serial.read(2)
        len_rcv = int.from_bytes(len_rcv, byteorder='big')

        content_rcv = self._serial.read(len_rcv-2)

        checksum_rcv = self._serial.read(2)
        if checksum_rcv != self.checksum(pid_rcv, len_rcv, content_rcv):
            raise Exception("Checksum Mismatch")

        return content_rcv



    def verify_password(self):
        # package_len
        package_len = 7

        self.send_packet(PID_COMMAND, package_len, IC_VERIFY_PASSWORD + self._password)

        content_rcv = self.recieve_packet()

        cc = content_rcv

        if cc == CC_SUCCESS:
            print("Verified")
        elif cc == CC_ERROR:
            raise Exception("error when receiving package")
        elif cc == CC_WRONG_PASS:
            raise Exception("Wrong Password")
        else:
            raise Exception("Unrecognised confirmation code")

    def generate_image(self):
        time.sleep(2)
        package_len = 3
        self.send_packet(PID_COMMAND, package_len, IC_GENERATE_IMAGE)

        content_rcv = self.recieve_packet()
        cc = content_rcv


        if cc == CC_SUCCESS:
            print("Finger Collection Success")
        elif cc == CC_ERROR:
            raise Exception("error when receiving package")
        elif cc == CC_FINGER_NOT_DETECTED:
            raise Exception("can’t detect finger")
        elif cc == CC_FAILED_TO_COLLECT_FINGER:
            raise Exception("fail to collect finger;")
        else:
            raise Exception("Unrecognised confirmation code")


sensor = Sensor('/dev/ttyUSB0', 57600)
sensor.generate_image()

