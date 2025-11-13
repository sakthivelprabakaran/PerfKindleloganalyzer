import json
from .profile import Profile


class ProfileManager:
    def __init__(self, filename="profiles.json"):
        self.filename = filename
        self.profiles = {}
        self.load_profiles()

    def load_profiles(self):
        try:
            with open(self.filename, "r") as f:
                profiles_data = json.load(f)
                for name, data in profiles_data.items():
                    self.profiles[name] = Profile(**data)
        except FileNotFoundError:
            pass

    def save_profiles(self):
        with open(self.filename, "w") as f:
            json.dump({name: profile.__dict__ for name, profile in self.profiles.items()}, f)

    def add_profile(self, profile):
        self.profiles[profile.name] = profile
        self.save_profiles()

    def get_profile(self, name):
        return self.profiles.get(name)

    def get_all_profiles(self):
        return list(self.profiles.values())
