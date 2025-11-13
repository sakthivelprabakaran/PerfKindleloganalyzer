class Profile:
    def __init__(
        self,
        name,
        type,
        host=None,
        port=None,
        username=None,
        password=None,
        private_key=None,
        auto_reconnect=False,
        baudrate=None,
        parity=None,
        stop_bits=None,
    ):
        self.name = name
        self.type = type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.auto_reconnect = auto_reconnect
        self.baudrate = baudrate
        self.parity = parity
        self.stop_bits = stop_bits
