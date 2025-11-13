from connections.ssh_connection import SshConnection
from connections.serial_connection import SerialConnection
from connections.worker import ConnectionWorker
from profiles.profile import Profile


class ConnectionManager:
    def __init__(self):
        self.connections = {}
        self.workers = {}

    def create_connection(self, profile):
        if profile.type == "ssh":
            connection = SshConnection(profile)
        elif profile.type == "serial":
            connection = SerialConnection(profile)
        else:
            raise ValueError(f"Unknown connection type: {profile.type}")

        connection.connect()
        if connection.connected:
            self.connections[profile.name] = connection
            worker = ConnectionWorker(connection)
            self.workers[profile.name] = worker
            return worker
        return None

    def close_connection(self, name):
        if name in self.connections:
            self.connections[name].disconnect()
            del self.connections[name]
        if name in self.workers:
            self.workers[name].stop()
            del self.workers[name]
