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

    def clear_all(self):
        self.results = []
        self.batch_results = {}
        self.loaded_files = []
        self.all_iterations_data = ""
        self.current_iteration = 1
        self.processed_test_cases.clear()
