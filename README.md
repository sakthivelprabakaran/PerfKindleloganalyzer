# Kindle Log Analyzer

## Overview

The Kindle Log Analyzer is a desktop application with a graphical user interface (GUI) built using PyQt5. It is designed to analyze log files from Kindle e-readers to measure performance metrics, such as the time taken for certain actions like page turns or swipes. The application provides a user-friendly way to process complex log data and extract meaningful performance indicators.

## Features

*   **Graphical User Interface:** An intuitive and easy-to-use interface for processing log files.
*   **Multiple Processing Modes:**
    *   **Single Entry:** Analyze log data for a single test case by pasting it directly into the application.
    *   **Batch Processing:** Process multiple log files at once for large-scale analysis.
*   **Flexible Calculation Modes:** Supports different types of user interactions for performance measurement:
    *   **Default (Button Up):** Measures the duration from a button release event.
    *   **Swipe (Button Down):** Measures the duration from a button press event.
    *   **Suspend (Power Button):** Measures the duration from a power button press event.
*   **Rich Results Display:** Presents analysis results in a structured and detailed manner, including:
    *   A summary tab with overall statistics.
    *   A detailed results table.
    *   A view of all extracted height and waveform data.
*   **Multiple Export Formats:** Export the analysis results to various formats:
    *   **PDF:** A comprehensive, human-readable report.
    *   **Excel:** A structured spreadsheet for batch results, ideal for further data analysis.
    *   **TXT:** A simple text file with the raw log data and a summary.
*   **Dark Mode:** A toggle for a dark-themed UI.

## How it Works

The core of the application is its log processing engine. Here's a step-by-step breakdown of how the analysis is performed:

1.  **Input:** The user provides log data, either by pasting it for a single entry or by selecting multiple log files for batch processing.
2.  **Iteration Splitting:** The log data is split into "iterations" using the `ITERATION_XX` pattern as a delimiter. Each iteration represents a single, complete action to be measured.
3.  **Event Parsing:** For each iteration, the application uses a specific parser based on the selected calculation mode:
    *   `DefaultEventParser`: Looks for a `button 1 up` event to determine the start time.
    *   `SwipeEventParser`: Looks for a `Sending button 1 down` event to determine the start time.
    *   `SuspendEventParser`: Looks for a `def:pbpress:time=...:Power button pressed` event to determine the start time.
4.  **Data Extraction:** The parser scans through the log lines of the iteration to extract key information:
    *   It identifies all screen update events (lines containing "Sending update") and extracts the `height` and `waveform` for each.
    *   Each update is associated with a `marker` number (e.g., `[123]`).
    *   It also extracts the `end time` for each marker from lines containing `update end marker=...`.
5.  **Duration Calculation:**
    *   To determine the final stop time for the action, the application finds the screen update with the maximum `height`. This is assumed to be the most significant update.
    *   The `marker` associated with this maximum height update is chosen as the "chosen marker".
    *   The `end time` corresponding to the "chosen marker" is used as the stop time for the calculation.
    *   The final duration is calculated as the difference between this `end time` and the `start time` extracted in step 3.
6.  **Output:** The calculated results, including the duration, start time, stop time, max height, and selected waveform, are displayed in the UI and can be exported.

## Usage

### Single Entry Mode

1.  Launch the application.
2.  Select the appropriate **Calculation Mode** from the dropdown (e.g., "Default (Button Up)").
3.  Enter a unique **Test Case Name**.
4.  Paste the log data for a single iteration into the **Log Data** text box.
5.  Click the **Add Iteration** button. The text box will clear, ready for the next iteration.
6.  Repeat steps 4-5 for all iterations of your test case.
7.  Once all iterations are added, click the **Process All** button.
8.  The results will be displayed in the tabs on the right.

### Batch Processing Mode

1.  Launch the application.
2.  Change the **Processing** mode to "Batch Files".
3.  Select the appropriate **Calculation Mode**.
4.  Click the **Select Files** button and choose one or more `.log` or `.txt` files.
5.  The selected files will appear in the list.
6.  Click the **Process All Files** button.
7.  The results for all files will be processed and displayed.

### Exporting Results

After processing the logs in either mode, you can export the results by clicking one of the buttons in the **Export Options** section.

## Export Formats

*   **PDF:** Generates a detailed, professional-looking report that is easy to share. It includes a summary table, detailed results for each iteration, and the original log content with important lines highlighted.
*   **Excel:** Available in batch mode, this export creates a `.xlsx` file with a summary of all processed log files. Each file is a row, with columns for each iteration's duration, the average duration, and a summary of the waveform patterns. This format is ideal for further data analysis, charting, or reporting.
*   **TXT:** A simple text file that includes a summary of the results and the original log content for each iteration. This is useful for a quick review or for use in other scripts.

## Dependencies

This project relies on the following Python libraries:

*   PyQt5
*   reportlab
*   openpyxl
*   matplotlib

These can be installed using pip:
```bash
pip install -r requirements.txt
```
