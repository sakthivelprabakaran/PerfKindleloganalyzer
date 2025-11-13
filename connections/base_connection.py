import abc


class BaseConnection(abc.ABC):
    def __init__(self, profile):
        self.profile = profile
        self._connected = False

    @property
    def connected(self):
        return self._connected

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass

    @abc.abstractmethod
    def read(self, max_bytes=1024):
        pass

    @abc.abstractmethod
    def write(self, data):
        pass
