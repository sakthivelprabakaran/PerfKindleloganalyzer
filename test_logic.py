import unittest
from logic.log_processor import process_log_iteration_data

class TestLogProcessor(unittest.TestCase):

    def test_default_mode_processing(self):
        log_lines = [
            "2023-10-27 10:00:00.123 [INFO] button 1 up 12345.678",
            "2023-10-27 10:00:00.250 [DEBUG] mxc_epdc_fb: [1]",
            "2023-10-27 10:00:00.200 [DEBUG] Sending update. height=800, waveform=DU",
            "2023-10-27 10:00:00.350 [DEBUG] mxc_epdc_fb: [2]",
            "2023-10-27 10:00:00.300 [DEBUG] Sending update. height=1200, waveform=GC16",
            "2023-10-27 10:00:00.800 [INFO] update end marker=1 end time=12345900",
            "2023-10-27 10:00:00.900 [INFO] update end marker=2 end time=12346000",
        ]
        result = process_log_iteration_data(log_lines, "1", "default")
        self.assertIsNotNone(result, "Default mode processing failed")
        self.assertAlmostEqual(result['duration'], 0.322, places=3)
        self.assertEqual(result['max_height'], 1200)
        self.assertEqual(result['marker'], "2")

    def test_swipe_mode_processing(self):
        log_lines = [
            "2023-10-27 10:01:00.200 [INFO] Sending button 1 down 54321.987",
            "2023-10-27 10:01:00.550 [DEBUG] mxc_epdc_fb: [10]",
            "2023-10-27 10:01:00.500 [DEBUG] Sending update. height=1024, waveform=A2",
            "2023-10-27 10:01:00.900 [INFO] update end marker=10 end time=54322887",
        ]
        result = process_log_iteration_data(log_lines, "1", "swipe")
        self.assertIsNotNone(result, "Swipe mode processing failed")
        self.assertAlmostEqual(result['duration'], 0.900, places=3)

    def test_suspend_mode_processing(self):
        log_lines = [
            "def:pbpress:time=1751099650.205:Power button pressed",
            "mxc_epdc_fb: [123]",
            "Sending update. height=1200, waveform=DU",
            "update end marker=123 end time=1751099651234",
        ]
        result = process_log_iteration_data(log_lines, "1", "suspend")
        self.assertIsNotNone(result, "Suspend mode processing failed")
        self.assertAlmostEqual(result['duration'], 1.029, places=3)

if __name__ == '__main__':
    unittest.main()
