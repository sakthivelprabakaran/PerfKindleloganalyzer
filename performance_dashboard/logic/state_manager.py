import json
import os
import numpy as np
import shutil

class NumpyJSONEncoder(json.JSONEncoder):
    """
    A custom JSON encoder to handle NumPy data types, which are not
    natively serializable by the default JSON library.
    """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyJSONEncoder, self).default(obj)

class StateManager:
    """Manages the state of the Performance Execution Dashboard."""
    def __init__(self):
        self.sessions = []
        self.current_session = None
        self.session_file_path = "performance_dashboard_sessions.json"
        self.load_sessions()

    def load_sessions(self):
        """
        Loads the list of saved sessions from a JSON file.
        If the file is corrupted, it backs it up and starts fresh.
        """
        if os.path.exists(self.session_file_path):
            try:
                with open(self.session_file_path, 'r') as f:
                    # If the file is empty, json.load will raise an error
                    if os.path.getsize(self.session_file_path) == 0:
                        self.sessions = []
                        return
                    self.sessions = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding session file: {e}. Backing up corrupted file.")
                try:
                    shutil.copy(self.session_file_path, f"{self.session_file_path}.bak")
                    os.remove(self.session_file_path) # Start with a fresh file
                except IOError as backup_e:
                    print(f"Could not back up corrupted file: {backup_e}")
                self.sessions = []
            except IOError as e:
                print(f"Error reading session file: {e}")
                self.sessions = []

    def save_sessions(self):
        """Saves the current sessions list to the JSON file using the custom encoder."""
        try:
            with open(self.session_file_path, 'w') as f:
                json.dump(self.sessions, f, indent=4, cls=NumpyJSONEncoder)
        except IOError as e:
            print(f"Error saving sessions: {e}")

    def create_new_session(self, project_path, device_name, week, build_details, priority):
        """Creates a new session and adds it to the list."""
        session_file_name = f"{priority}_{device_name}_Week_{week}.xlsx"
        new_session = {
            "project_path": project_path,
            "device_name": device_name,
            "week": week,
            "build_details": build_details,
            "priority": priority,
            "file_name": session_file_name,
            "status": "In Progress",
            "current_test_case_index": 0,
        }
        self.sessions.append(new_session)
        self.current_session = new_session
        self.save_sessions()
        return new_session

    def set_current_session(self, session_data):
        """Sets the currently active session."""
        self.current_session = session_data

    def update_current_session(self, key, value):
        """Updates a value in the current session and saves."""
        if self.current_session:
            self.current_session[key] = value
            for i, session in enumerate(self.sessions):
                if session['file_name'] == self.current_session['file_name']:
                    self.sessions[i] = self.current_session
                    break
            self.save_sessions()

    def get_current_test_case_index(self):
        return self.current_session.get('current_test_case_index', 0) if self.current_session else 0

    def get_active_sheet(self):
        """Returns the 'priority' which is used as the sheet name for the current session."""
        return self.current_session.get('priority', 'P0') if self.current_session else 'P0'

    def get_session_by_filename(self, filename):
        """Finds and returns a session from the list by its filename."""
        for session in self.sessions:
            if session.get('file_name') == filename:
                return session
        return None

    def remove_session_by_filename(self, filename):
        """Removes a session from the list by its filename and saves the state."""
        session_to_remove = self.get_session_by_filename(filename)
        if session_to_remove:
            self.sessions.remove(session_to_remove)
            self.save_sessions()
            return True
        return False