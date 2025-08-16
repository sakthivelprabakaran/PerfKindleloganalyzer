import re
from PyQt5.QtCore import QThread, pyqtSignal
from logic.event_parser import DefaultEventParser, SwipeEventParser, SuspendEventParser

class LogProcessor(QThread):
    """Enhanced log processor with original log storage and bug fixes."""
    progress_updated = pyqtSignal(int)
    # The signal now emits a dictionary containing results and an optional filename
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    # Added filename parameter to handle batch processing safely
    def __init__(self, log_content, mode="default", filename=None):
        super().__init__()
        self.log_content = log_content
        self.mode = mode
        self.filename = filename # Store the filename for this specific job
        self.results_data = []

    def run(self):
        """Processes the log content without blocking the main thread."""
        try:
            self.progress_updated.emit(10)

            # The logic for splitting iterations remains the same
            iterations = re.split(r'ITERATION_(\d+)', self.log_content)[1:]
            if not iterations:
                iterations = ["01", self.log_content]

            self.progress_updated.emit(30)

            iteration_pairs = []
            for i in range(0, len(iterations), 2):
                if i + 1 < len(iterations):
                    iteration_num = iterations[i]
                    iteration_content = iterations[i+1]
                    iteration_pairs.append((iteration_num, iteration_content))

            self.progress_updated.emit(50)

            results = []
            total_iterations = len(iteration_pairs)

            for idx, (iteration_num, iteration_content) in enumerate(iteration_pairs):
                lines = iteration_content.split('\n')
                result = self.process_iteration(lines, iteration_num, self.mode)

                if result:
                    result['original_log'] = iteration_content.strip()
                    results.append(result)

                progress = 50 + (idx + 1) * 40 // (total_iterations or 1)
                self.progress_updated.emit(progress)

            self.results_data = results
            self.progress_updated.emit(100)
            
            # Emit the results along with the filename to avoid race conditions
            self.result_ready.emit({
                'results': results,
                'total_iterations': len(iteration_pairs),
                'filename': self.filename
            })

        except Exception as e:
            self.error_occurred.emit(str(e))

    def process_iteration(self, lines, iteration_num, mode="default"):
        """Process a single iteration with corrected duration calculation."""
        
        parser_map = {
            "suspend": SuspendEventParser(),
            "swipe": SwipeEventParser(),
            "default": DefaultEventParser()
        }
        parser = parser_map.get(mode, DefaultEventParser())

        start_time = None
        start_line = None
        end_times_by_marker = {}
        heights_by_marker = {}
        current_marker = None

        for line in lines:
            if not line.strip():
                continue

            if not start_time:
                possible_start = parser.extract_start_timestamp(line)
                if possible_start:
                    start_time = possible_start
                    start_line = line.strip()

            marker = parser.extract_marker(line)
            if marker:
                current_marker = marker

            if "Sending update" in line and current_marker:
                height_waveform = parser.extract_height_and_waveform(line)
                if height_waveform:
                    heights_by_marker[current_marker] = {
                        'height': height_waveform['height'],
                        'waveform': height_waveform.get('waveform', "unknown") or "unknown",
                        'line': line.strip()
                    }

            if "update end marker=" in line and "end time=" in line:
                end_marker_match = re.search(r'update end marker=(\d+)', line)
                if end_marker_match:
                    end_marker = end_marker_match.group(1)
                    end_time = parser.extract_end_timestamp(line)
                    if end_time:
                        end_times_by_marker[end_marker] = {
                            'time': end_time,
                            'line': line.strip()
                        }

        if not start_time or not heights_by_marker or not end_times_by_marker:
            return None

        valid_heights = {m: i for m, i in heights_by_marker.items() if i['waveform'].lower() != "unknown"}
        if not valid_heights:
            valid_heights = heights_by_marker
        if not valid_heights:
            return None

        max_height = max(info['height'] for info in valid_heights.values())
        max_height_markers = [m for m, i in valid_heights.items() if i['height'] == max_height]
        max_height_markers.sort(key=lambda m: int(m) if m.isdigit() else 0)
        chosen_marker = max_height_markers[-1] if max_height_markers else list(valid_heights.keys())[0]
        max_height_info = valid_heights[chosen_marker]

        if chosen_marker in end_times_by_marker:
            max_height_end_time = end_times_by_marker[chosen_marker]['time']
        else:
            if end_times_by_marker:
                max_height_end_time = max(end_times_by_marker.values(), key=lambda x: x['time'])['time']
            else:
                return None

        # *** BUG FIX: Correctly handle timestamp rollover ***
        # The timestamps are 6 digits, so the rollover boundary is 1,000,000.
        duration = max_height_end_time - start_time
        if duration < 0:
            duration += 1000000 # Add the boundary value to correct for rollover

        duration_sec = duration / 1000.0

        return {
            'iteration': int(iteration_num),
            'start': start_time,
            'stop': max_height_end_time,
            'marker': chosen_marker,
            'duration': duration_sec,
            'max_height': max_height_info['height'],
            'max_height_waveform': max_height_info['waveform'],
            'start_line': start_line,
            'all_heights': [{'marker': m, 'height': h['height'], 'waveform': h['waveform']} for m, h in heights_by_marker.items()],
            'mode': mode,
            'all_end_times': end_times_by_marker
        }
