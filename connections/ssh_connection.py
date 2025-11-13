from .base_connection import BaseConnection
import paramiko


class SshConnection(BaseConnection):
    def __init__(self, profile):
        super().__init__(profile)
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.shell = None

    def connect(self):
        try:
            pkey = None
            if self.profile.private_key:
                pkey = paramiko.RSAKey.from_private_key_file(self.profile.private_key)

            self.client.connect(
                hostname=self.profile.host,
                port=self.profile.port,
                username=self.profile.username,
                password=self.profile.password,
                pkey=pkey,
            )
            self.shell = self.client.invoke_shell()
            self._connected = True
        except Exception as e:
            self._connected = False
            print(f"Error connecting to {self.profile.host}: {e}")

    def disconnect(self):
        if self.client:
            self.client.close()
        self._connected = False

    def read(self, max_bytes=1024):
        if self.shell and self.shell.recv_ready():
            return self.shell.recv(max_bytes)
        return None

    def write(self, data):
        if self.shell and self.shell.send_ready():
            self.shell.send(data)
