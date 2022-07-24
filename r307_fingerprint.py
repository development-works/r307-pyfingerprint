# create an interhface to communicate with sensor via my pc
from serial import Serial
import time
from PIL import Image

HEADER = bytes.fromhex('EF01')

PID_COMMAND = bytes.fromhex('01')
PID_ACK = bytes.fromhex('07')
PID_DATA = bytes.fromhex('02')
PID_EOD = bytes.fromhex('08')

IC_VERIFY_PASSWORD = bytes.fromhex('13')
IC_GENERATE_IMAGE = bytes.fromhex('01')
IC_DOWNLOAD_IMAGE = bytes.fromhex('0a')
IC_GENERATE_CHARACTERISTICS = bytes.fromhex('02')
IC_GENERATE_TEMPLATE = bytes.fromhex('05')
IC_DOWNLOAD_CHAR_BUFFER = bytes.fromhex('08')

CC_SUCCESS = bytes.fromhex('00')
CC_ERROR = bytes.fromhex('01')
CC_WRONG_PASS = bytes.fromhex('13')
CC_FINGER_NOT_DETECTED = bytes.fromhex('02')
CC_FAILED_TO_COLLECT_FINGER = bytes.fromhex('03')
CC_FAILED_DOWNLOAD_IMAGE = bytes.fromhex('0e')
CC_DISORDERED_FINGERPRINT = bytes.fromhex('06')
CC_VERY_SMALL_FINGERPRINT = bytes.fromhex('07')
CC_INVALID_PRIMARY_IMAGE = bytes.fromhex('15')
CC_CHAR_MISMATCH = bytes.fromhex('0a')
CC_TEMPLATE_DWNLD_ERR = bytes.fromhex('0d')

CHAR_BUFFER_1 = bytes.fromhex('01')
CHAR_BUFFER_2 = bytes.fromhex('02')


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

    def verify_password(self):

        self.send_packet(PID_COMMAND, IC_VERIFY_PASSWORD + self._password)

        pid_rcv, content_rcv = self.receive_packet()

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
        self.send_packet(PID_COMMAND, IC_GENERATE_IMAGE)

        pid_rcv, content_rcv = self.receive_packet()
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

    def download_image(self):
        self.send_packet(PID_COMMAND, IC_DOWNLOAD_IMAGE)
        pid_rcv, content_rcv = self.receive_packet()

        cc = content_rcv

        if cc == CC_SUCCESS:
            print("Downloading the fingerprint image")
        elif cc == CC_ERROR:
            raise Exception("error when receiving package for downloading "
                            "image")
        elif cc == CC_FAILED_DOWNLOAD_IMAGE:
            raise Exception("Could not download image")
        else:
            raise Exception("Unrecognised confirmation code")

        image_rcv = bytes()

        with open('temp/img.jpg', 'ab') as file:
            while True:
                pid_rcv, content_rcv = self.receive_packet()
                image_rcv = image_rcv + content_rcv

                if pid_rcv == PID_EOD:
                    print("End of Data reached")
                    break

        # TODO: Save the File in image form

        # finger_img = Image.frombytes("L", (256, 288), image_rcv)
        # finger_img.save("./temp/FingerPrintImage.jpg")

    def generate_charfile_image(self, buffer_id):
        self.send_packet(PID_COMMAND,
                         IC_GENERATE_CHARACTERISTICS + buffer_id)

        pid_rcv, content_rcv = self.receive_packet()
        cc = content_rcv

        if cc == CC_SUCCESS:
            print("generate character file complete;")
        elif cc == CC_ERROR:
            raise Exception("error when receiving package for downloading "
                            "image")
        elif cc == CC_DISORDERED_FINGERPRINT:
            raise Exception("fail to generate character file due to the "
                            "over-disorderly fingerprint image")
        elif cc == CC_VERY_SMALL_FINGERPRINT:
            raise Exception("fail to generate character file due to lackness "
                            "of character point or over-smallness of "
                            "fingerprint image")
        elif cc == CC_INVALID_PRIMARY_IMAGE:
            raise Exception("fail to generate the image for the lackness of "
                            "valid primary image")
        else:
            raise Exception("Unrecognised confirmation code")

    def generate_template(self):
        self.send_packet(PID_COMMAND,
                         IC_GENERATE_TEMPLATE)

        pid_rcv, content_rcv = self.receive_packet()
        cc = content_rcv

        if cc == CC_SUCCESS:
            print("generate template complete")
        elif cc == CC_ERROR:
            raise Exception("error when receiving package for downloading "
                            "image")
        elif cc == CC_CHAR_MISMATCH:
            raise Exception("fail to combine the character files. That’s, "
                            "the character files don’t belong to one finger")
        else:
            raise Exception("Unrecognised confirmation code")

    def download_char_buffer(self, buffer_id):
        self.send_packet(PID_COMMAND, IC_DOWNLOAD_CHAR_BUFFER + buffer_id)
        pid_rcv, content_rcv = self.receive_packet()

        cc = content_rcv

        if cc == CC_SUCCESS:
            print("Downloading the fingerprint image")
        elif cc == CC_ERROR:
            raise Exception("error when receiving package for downloading "
                            "image")
        elif cc == CC_TEMPLATE_DWNLD_ERR:
            raise Exception("Error when downloading template")
        else:
            raise Exception("Unrecognised confirmation code")

        char_rcv = bytes()

        while True:
            pid_rcv, content_rcv = self.receive_packet()
            char_rcv = char_rcv + content_rcv

            if pid_rcv == PID_EOD:
                print("End of Data reached")
                break

        print(char_rcv)

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

    def send_packet(self, pid, content):

        package_len = len(content) + 2

        checksum = self.checksum(pid, package_len, content)
        # Getting value of checksum

        self._serial.write(HEADER)
        self._serial.write(self._address)
        self._serial.write(pid)
        self._serial.write(package_len.to_bytes(2, byteorder='big'))
        self._serial.write(content)
        self._serial.write(checksum)

    def receive_packet(self):
        header_rcv = self._serial.read(2)
        if header_rcv != HEADER:
            raise Exception("Acknowledgment Header invalid")

        address_rcv = self._serial.read(4)
        if address_rcv != self._address:
            raise Exception("Address is invalid")

        pid_rcv = self._serial.read(1)
        '''if pid_rcv != PID_ACK:
            raise Exception("PID is invalid")'''

        len_rcv = self._serial.read(2)
        len_rcv = int.from_bytes(len_rcv, byteorder='big')

        content_rcv = self._serial.read(len_rcv - 2)

        checksum_rcv = self._serial.read(2)
        if checksum_rcv != self.checksum(pid_rcv, len_rcv, content_rcv):
            raise Exception("Checksum Mismatch")

        return pid_rcv, content_rcv


sensor = Sensor('/dev/ttyUSB0', 57600)
# sensor.generate_image()
# sensor.download_image()
# sensor.generate_charfile_image(CHAR_BUFFER_1)
# sensor.generate_charfile_image(CHAR_BUFFER_2)
# sensor.generate_template()
sensor.download_char_buffer(CHAR_BUFFER_1)
