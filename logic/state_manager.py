import json

class StateManager:
    def __init__(self):
        self.results = []
        self.batch_results = {}
        self.loaded_files = []
        self.current_iteration = 1
        self.all_iterations_data = ""
        self.test_case_title = ""
        self.current_mode = "default"
        self.dark_mode = False
        self.processed_test_cases = set()
        self.threads = []

    def to_dict(self):
        """Convert state to a serializable dictionary."""
        return {
            'results': self.results,
            'batch_results': self.batch_results,
            'loaded_files': self.loaded_files,
            'current_iteration': self.current_iteration,
            'all_iterations_data': self.all_iterations_data,
            'test_case_title': self.test_case_title,
            'current_mode': self.current_mode,
            'dark_mode': self.dark_mode,
            'processed_test_cases': list(self.processed_test_cases),
        }

    def from_dict(self, data):
        """Load state from a dictionary."""
        self.results = data.get('results', [])
        self.batch_results = data.get('batch_results', {})
        self.loaded_files = data.get('loaded_files', [])
        self.current_iteration = data.get('current_iteration', 1)
        self.all_iterations_data = data.get('all_iterations_data', "")
        self.test_case_title = data.get('test_case_title', "")
        self.current_mode = data.get('current_mode', "default")
        self.dark_mode = data.get('dark_mode', False)
        self.processed_test_cases = set(data.get('processed_test_cases', []))

    def clear_all(self):
        self.results = []
        self.batch_results = {}
        self.loaded_files = []
        self.all_iterations_data = ""
        self.current_iteration = 1
        self.processed_test_cases.clear()
