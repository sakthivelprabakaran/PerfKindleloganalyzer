"""
event_parser.py - Module for parsing Kindle log events
This module contains classes for extracting timestamps and other data from log lines
"""
import re

class BaseEventParser:
    """Base class for parsing log events with common extraction methods"""

    def extract_marker(self, line):
        """Extract marker number from log line"""
        match1 = re.search(r'EPDC\]\[(\d+)\]', line)
        if match1:
            return match1.group(1)

        match2 = re.search(r'mxc_epdc_fb: \[(\d+)\]', line)
        if match2:
            return match2.group(1)

        return None

    def extract_height_and_waveform(self, line):
        """Extract height and waveform information from log line"""
        height_match = re.search(r'height=(\d+)', line)
        if not height_match:
            height_match = re.search(r'width=\d+, height=(\d+)', line)

        waveform_patterns = [
            r'new waveform = (?:0x)?[\da-f]+ \(([\w_() ]+)\)',
            r'waveform:(?:0x)?[\da-f]+ \(([\w_() ]+)\)',
            r'waveform=(?:0x)?[\da-f]+ \(([\w_() ]+)\)',
            r'Sending update\. waveform:(?:0x)?[\da-f]+ \(([\w_() ]+)\)'
        ]

        waveform_name = None
        for pattern in waveform_patterns:
            match = re.search(pattern, line)
            if match:
                waveform_name = match.group(1).strip()
                break

        if height_match:
            height = int(height_match.group(1))
            return {
                'height': height,
                'waveform': waveform_name if waveform_name else "unknown"
            }
        return None

    def extract_end_timestamp(self, line):
        """Extract end timestamp from log line"""
        match = re.search(r'end time=(\d+)', line)
        if match:
            timestamp_str = match.group(1)
            last_6 = timestamp_str[-6:]
            return int(last_6)
        return None

    def extract_start_timestamp(self, line):
        """Base method for extracting start timestamp - to be implemented by subclasses"""
        return None

class DefaultEventParser(BaseEventParser):
    """Parser for default mode (Button Up)"""

    def extract_start_timestamp(self, line):
        """Extract start timestamp from "button 1 up" event"""
        match = re.search(r'button 1 up (\d+\.\d+)', line)
        if match:
            timestamp_str = match.group(1)
            parts = timestamp_str.split('.')
            if len(parts) == 2:
                last_3_first = parts[0][-3:]
                first_3_second = parts[1][:3]
                result = int(last_3_first + first_3_second)
                return result
        return None

class SwipeEventParser(BaseEventParser):
    """Parser for swipe mode (Button Down)"""

    def extract_start_timestamp(self, line):
        """Extract start timestamp from "Sending button 1 down" event"""
        match = re.search(r'Sending button 1 down (\d+\.\d+)', line)
        if match:
            timestamp_str = match.group(1)
            parts = timestamp_str.split('.')
            if len(parts) == 2:
                last_3_first = parts[0][-3:]
                first_3_second = parts[1][:3]
                result = int(last_3_first + first_3_second)
                return result
        return None

class SuspendEventParser(BaseEventParser):
    """Parser for suspend mode (Power Button)"""

    def extract_start_timestamp(self, line):
        """Extract start timestamp from power button press event"""
        match = re.search(r'def:pbpress:time=(\d+\.\d+):Power button pressed', line)
        if match:
            timestamp_str = match.group(1)
            parts = timestamp_str.split('.')
            if len(parts) == 2:
                before_dot = parts[0]
                after_dot = parts[1][:3]
                last_digits_before = before_dot[-3:]
                result = int(last_digits_before + after_dot)
                return result
        return None