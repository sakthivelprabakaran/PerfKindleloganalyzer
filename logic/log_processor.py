import re
from PyQt5.QtCore import QThread, pyqtSignal
from logic.event_parser import DefaultEventParser, SwipeEventParser, SuspendEventParser

class LogProcessor(QThread):
    """Enhanced log processor with original log storage"""
    progress_updated = pyqtSignal(int)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, log_content, mode="default"):
        super().__init__()
        self.log_content = log_content
        self.mode = mode

    def run(self):
        try:
            self.progress_updated.emit(10)

            # Split content into iterations while preserving original content
            iterations = re.split(r'ITERATION_(\d+)', self.log_content)[1:]

            if not iterations:
                iterations = ["01", self.log_content]

            self.progress_updated.emit(30)

            # Pair iteration numbers with content
            iteration_pairs = []
            for i in range(0, len(iterations), 2):
                if i+1 < len(iterations):
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
                    # Store original log content with the result
                    result['original_log'] = iteration_content.strip()
                    results.append(result)

                progress = 50 + (idx + 1) * 40 // total_iterations
                self.progress_updated.emit(progress)

            self.progress_updated.emit(100)
            self.result_ready.emit({'results': results, 'total_iterations': len(iteration_pairs)})

        except Exception as e:
            self.error_occurred.emit(str(e))

    def process_iteration(self, lines, iteration_num, mode="default"):
        """Process a single iteration with fixed suspend parsing"""

        # Get appropriate parser
        if mode == "suspend":
            parser = SuspendEventParser()
        elif mode == "swipe":
            parser = SwipeEventParser()
        else:
            parser = DefaultEventParser()

        start_time = None
        start_line = None  # Store the line that contains start time for highlighting
        end_times_by_marker = {}
        heights_by_marker = {}
        current_marker = None

        for line in lines:
            if not line.strip():
                continue

            # Check for start time based on the parser's implementation
            if not start_time:
                possible_start = parser.extract_start_timestamp(line)
                if possible_start:
                    start_time = possible_start
                    start_line = line.strip()  # Store the start line for highlighting

            marker = parser.extract_marker(line)
            if marker:
                current_marker = marker

            if "Sending update" in line and current_marker:
                height_waveform = parser.extract_height_and_waveform(line)
                if height_waveform:
                    height = height_waveform['height']
                    waveform = height_waveform['waveform']

                    heights_by_marker[current_marker] = {
                        'height': height,
                        'waveform': waveform if waveform and waveform != "auto" else "unknown",
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

        # Filter out markers with "unknown" waveforms
        valid_heights = {
            marker: info for marker, info in heights_by_marker.items()
            if info['waveform'].lower() != "unknown"
        }

        # If no valid waveforms found, use all heights as a fallback
        if not valid_heights:
            valid_heights = heights_by_marker

        if not valid_heights:
            return None

        # Find the marker with the maximum height among valid waveforms
        max_height = max(info['height'] for info in valid_heights.values())
        max_height_markers = [marker for marker, info in valid_heights.items()
                             if info['height'] == max_height]

        max_height_markers.sort(key=lambda m: int(m) if m.isdigit() else 0)
        chosen_marker = max_height_markers[-1] if max_height_markers else list(valid_heights.keys())[0]

        max_height_info = valid_heights[chosen_marker]

        # Get the end time for the chosen marker
        if chosen_marker in end_times_by_marker:
            max_height_end_time = end_times_by_marker[chosen_marker]['time']
        else:
            # If no end time for the chosen marker, use the maximum end time
            if end_times_by_marker:
                max_height_end_time = max(end_times_by_marker.values(), key=lambda x: x['time'])['time']
            else:
                return None

        # Calculate duration
        duration = max_height_end_time - start_time
        if duration < 0:
            duration += 1000000  # Handle rollover

        # Convert duration from milliseconds to seconds
        duration = duration / 1000.0

        return {
            'iteration': int(iteration_num),  # Convert to integer here
            'start': start_time,
            'stop': max_height_end_time,
            'marker': chosen_marker,
            'duration': duration,
            'max_height': max_height_info['height'],
            'max_height_waveform': max_height_info['waveform'],
            'start_line': start_line,  # For PDF highlighting
            'all_heights': [{'marker': m, 'height': h['height'], 'waveform': h['waveform']}
                           for m, h in heights_by_marker.items()],
            'mode': mode,
            'all_end_times': end_times_by_marker
        }