from .base_connection import BaseConnection
import serial


class SerialConnection(BaseConnection):
    def __init__(self, profile):
        super().__init__(profile)
        self.serial = serial.Serial()

    def connect(self):
        try:
            self.serial.port = self.profile.port
            self.serial.baudrate = self.profile.baudrate
            self.serial.parity = self.get_parity()
            self.serial.stopbits = self.get_stop_bits()
            self.serial.open()
            self._connected = True
        except Exception as e:
            self._connected = False
            print(f"Error connecting to {self.profile.port}: {e}")

    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
        self._connected = False

    def read(self, max_bytes=1024):
        if self.serial and self.serial.in_waiting > 0:
            return self.serial.read(min(max_bytes, self.serial.in_waiting))
        return None

    def write(self, data):
        if self.serial and self.serial.is_open:
            self.serial.write(data)

    def get_parity(self):
        if self.profile.parity == "None":
            return serial.PARITY_NONE
        elif self.profile.parity == "Even":
            return serial.PARITY_EVEN
        elif self.profile.parity == "Odd":
            return serial.PARITY_ODD
        return serial.PARITY_NONE

    def get_stop_bits(self):
        if self.profile.stop_bits == "1":
            return serial.STOPBITS_ONE
        elif self.profile.stop_bits == "1.5":
            return serial.STOPBITS_ONE_POINT_FIVE
        elif self.profile.stop_bits == "2":
            return serial.STOPBITS_TWO
        return serial.STOPBITS_ONE
