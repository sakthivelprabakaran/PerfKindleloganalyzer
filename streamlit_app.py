import streamlit as st
from logic.log_processor import process_log_iteration_data
from logic.state_manager import StateManager
import pandas as pd
import re
import difflib
from utils.pdf_export import PdfExporter
from utils.txt_export import TxtExporter
from utils.excel_export import ExcelExporter
import io
import zipfile

def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def add_iteration_callback():
    log_content = st.session_state.log_input_widget
    if log_content and log_content.strip():
        iteration_header = f"\nITERATION_{st.session_state.current_iteration:02d}\n"
        st.session_state.all_iterations_data += iteration_header + log_content + "\n"
        st.session_state.current_iteration += 1
        st.session_state.status = f"Added iteration {st.session_state.current_iteration - 1}. Ready for next."
        st.session_state.log_input_widget = ""
    else:
        st.session_state.status = "Cannot add empty log. Please enter log data."

# --- State Management ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.dark_mode = False
    st.session_state.processing_mode = "Single Entry"
    st.session_state.calculation_mode = "Default (Button Up)"
    st.session_state.test_case_name = ""
    st.session_state.log_input = ""
    st.session_state.all_iterations_data = ""
    st.session_state.current_iteration = 1
    st.session_state.results = []
    st.session_state.batch_results = {}
    st.session_state.status = "Ready"

st.set_page_config(layout="wide")

load_css("style.css")

# JavaScript to apply the theme
theme_js = f"""
<script>
    function applyTheme() {{
        const theme = {'"dark"' if st.session_state.dark_mode else '"light"'};
        document.body.setAttribute('data-theme', theme);
    }}
    applyTheme();
</script>
"""
st.markdown(theme_js, unsafe_allow_html=True)


st.title("Kindle Log Analyzer (Streamlit Version)")

# --- Sidebar ---
st.sidebar.title("📁 Input & Processing")

# Header with dark mode toggle
st.sidebar.header("🔧 Configuration")
dark_mode = st.sidebar.checkbox("Dark Mode", key="dark_mode")

# Processing and Calculation Mode
processing_mode = st.sidebar.selectbox(
    "Processing Mode",
    ["Single Entry", "Batch Files"],
    key="processing_mode"
)

calculation_mode = st.sidebar.selectbox(
    "Calculation Mode",
    ["Default (Button Up)", "Swipe (Button Down)", "Suspend (Power Button)"],
    key="calculation_mode"
)


if processing_mode == "Single Entry":
    st.sidebar.header("📝 Single Entry")
    test_case_name = st.sidebar.text_input(
        "Test Case Name",
        placeholder="e.g., Kindle_Performance_Test",
        key="test_case_name"
    )
    log_input = st.sidebar.text_area(
        "Log Data",
        placeholder="Paste log data here...",
        height=150,
        key="log_input_widget"
    )
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.button("➕ Add Iteration", use_container_width=True, on_click=add_iteration_callback)

    with col2:
        if st.button("🔄 Process All", use_container_width=True, disabled=not st.session_state.all_iterations_data):
            with st.spinner("Processing iterations..."):
                mode_map = {
                    "Default (Button Up)": "default",
                    "Swipe (Button Down)": "swipe",
                    "Suspend (Power Button)": "suspend"
                }
                current_mode = mode_map.get(st.session_state.calculation_mode, "default")

                iterations = re.split(r'ITERATION_(\\d+)', st.session_state.all_iterations_data)[1:]
                if not iterations:
                    iterations = ["01", st.session_state.all_iterations_data]

                iteration_pairs = []
                for i in range(0, len(iterations), 2):
                    if i + 1 < len(iterations):
                        iteration_num = iterations[i]
                        iteration_content = iterations[i+1]
                        iteration_pairs.append((iteration_num, iteration_content))

                results = []
                for idx, (iteration_num, iteration_content) in enumerate(iteration_pairs):
                    lines = iteration_content.split('\\n')
                    result = process_log_iteration_data(lines, iteration_num, current_mode)
                    if result:
                        result['original_log'] = iteration_content.strip()
                        results.append(result)

                st.session_state.results = results
                st.session_state.status = f"Processed {len(results)} iterations successfully."
            st.rerun()

else: # Batch Files
    st.sidebar.header("📂 Batch Processing")
    uploaded_files = st.sidebar.file_uploader(
        "Select Log Files",
        accept_multiple_files=True,
        type=['.log', '.txt'],
        key="uploaded_files"
    )
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("⚡ Process All Files", use_container_width=True, disabled=not st.session_state.uploaded_files):
            with st.spinner("Processing batch files..."):
                st.session_state.batch_results = {}
                mode_map = {
                    "Default (Button Up)": "default",
                    "Swipe (Button Down)": "swipe",
                    "Suspend (Power Button)": "suspend"
                }
                current_mode = mode_map.get(st.session_state.calculation_mode, "default")

                for uploaded_file in st.session_state.uploaded_files:
                    content = uploaded_file.read().decode("utf-8")

                    iterations = re.split(r'ITERATION_(\\d+)', content)[1:]
                    if not iterations:
                        iterations = ["01", content]

                    iteration_pairs = []
                    for i in range(0, len(iterations), 2):
                        if i + 1 < len(iterations):
                            iteration_num = iterations[i]
                            iteration_content = iterations[i+1]
                            iteration_pairs.append((iteration_num, iteration_content))

                    file_results = []
                    for idx, (iteration_num, iteration_content) in enumerate(iteration_pairs):
                        lines = iteration_content.split('\\n')
                        result = process_log_iteration_data(lines, iteration_num, current_mode)
                        if result:
                            result['original_log'] = iteration_content.strip()
                            file_results.append(result)

                    st.session_state.batch_results[uploaded_file.name] = file_results

                st.session_state.status = f"Processed {len(st.session_state.uploaded_files)} files."
            st.rerun()
    with col2:
        if st.button("🗑️ Clear Files", use_container_width=True):
            st.session_state.uploaded_files = []
            st.rerun()


st.sidebar.header("📊 Status")
st.sidebar.info(st.session_state.status)

st.sidebar.header("💾 Export Options")

# Determine if there are any results to export
results_exist = st.session_state.results or st.session_state.batch_results

# PDF Export
pdf_exporter = PdfExporter()
if st.session_state.processing_mode == "Single Entry":
    if results_exist:
        pdf_bytes = pdf_exporter.generate_pdf_bytes(st.session_state.results, st.session_state.calculation_mode)
        st.sidebar.download_button(
            label="Export PDF Report",
            data=pdf_bytes,
            file_name=f"{st.session_state.test_case_name or 'report'}.pdf",
            mime="application/pdf"
        )
    else:
        st.sidebar.button("Export PDF Report", disabled=True)
else: # Batch Mode
    if results_exist:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for filename, results in st.session_state.batch_results.items():
                # Add PDF to zip
                pdf_bytes = pdf_exporter.generate_pdf_bytes(results, st.session_state.calculation_mode)
                zip_file.writestr(f"{filename}_report.pdf", pdf_bytes)
                # Add TXT to zip
                txt_exporter = TxtExporter()
                txt_bytes = txt_exporter.generate_txt_bytes(results)
                zip_file.writestr(f"{filename}_report.txt", txt_bytes)

        st.sidebar.download_button(
            label="Export All Reports (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="kindle_batch_reports.zip",
            mime="application/zip",
        )
    else:
        st.sidebar.button("Export All Reports (ZIP)", disabled=True)

# TXT Export (Single Entry only)
if st.session_state.processing_mode == "Single Entry" and results_exist:
    txt_exporter = TxtExporter()
    txt_bytes = txt_exporter.generate_txt_bytes(st.session_state.results)
    st.sidebar.download_button(
        label="Export TXT Report",
        data=txt_bytes,
        file_name=f"{st.session_state.test_case_name or 'report'}.txt",
        mime="text/plain"
    )
else:
    st.sidebar.button("Export TXT Report", disabled=True)


# Excel Export (Batch Mode only)
if st.session_state.processing_mode == "Batch Files" and results_exist:
    excel_exporter = ExcelExporter()
    excel_bytes = excel_exporter.generate_excel_bytes(st.session_state.batch_results)
    st.sidebar.download_button(
        label="Export Excel Report",
        data=excel_bytes,
        file_name="kindle_batch_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.sidebar.button("Export Excel Report", disabled=True)


# Clear All button
if st.sidebar.button("🗑️ Clear All"):
    for key in st.session_state.keys():
        if key != 'initialized':
            del st.session_state[key]
    st.rerun()


# --- Main Panel ---
if not st.session_state.results and not st.session_state.batch_results:
    st.info("Awaiting processing. Please add data and process on the left.")
else:
    tabs = st.tabs([
        "📊 Summary",
        "📋 Main Results",
        "📦 Waveform Boxes",
        "📏 Heights & Waveforms",
        "📁 Batch Results",
        "⚖️ Comparison"
    ])
    tab1, tab2, tab3, tab4, tab5, tab6 = tabs

    with tab1:
        st.header("Processing Summary")

        def generate_summary_html(results, test_case_name):
            if not results:
                return "<p>No results to summarize.</p>"

            total_iterations = len(results)
            durations = [r['duration'] for r in results]
            avg_duration = sum(durations) / total_iterations
            min_duration = min(durations)
            max_duration = max(durations)

            summary_html = f"""
            <h4>📊 Summary for {test_case_name}</h4>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width:100%;">
                <tr><td><b>Test Case:</b></td><td>{test_case_name}</td></tr>
                <tr><td><b>Processing Mode:</b></td><td>{st.session_state.calculation_mode}</td></tr>
                <tr><td><b>Total Iterations:</b></td><td>{total_iterations}</td></tr>
                <tr><td><b>Average Duration:</b></td><td style="background-color: yellow;">{avg_duration:.3f} s</td></tr>
                <tr><td><b>Min Duration:</b></td><td>{min_duration:.3f} s</td></tr>
                <tr><td><b>Max Duration:</b></td><td>{max_duration:.3f} s</td></tr>
            </table>
            <br>
            """
            return summary_html

        if st.session_state.processing_mode == "Single Entry":
            if st.session_state.results:
                summary_html = generate_summary_html(st.session_state.results, st.session_state.test_case_name or "Single Entry")
                st.markdown(summary_html, unsafe_allow_html=True)
            else:
                st.info("No data to display.")
        else: # Batch Mode
            if st.session_state.batch_results:
                for filename, results in st.session_state.batch_results.items():
                    summary_html = generate_summary_html(results, filename)
                    st.markdown(summary_html, unsafe_allow_html=True)
                    st.markdown("---")
            else:
                st.info("No data to display.")

    with tab2:
        st.header("Detailed Results")
        if st.session_state.processing_mode == "Single Entry":
            if st.session_state.results:
                df = pd.DataFrame(st.session_state.results)
                display_df = df[['iteration', 'duration', 'start', 'stop', 'marker', 'max_height', 'max_height_waveform', 'mode']]
                st.dataframe(display_df)
            else:
                st.info("No results to display. Process data in the sidebar.")
        else: # Batch Mode
            if st.session_state.batch_results:
                for filename, results in st.session_state.batch_results.items():
                    st.subheader(f"Results for: {filename}")
                    if results:
                        df = pd.DataFrame(results)
                        display_df = df[['iteration', 'duration', 'start', 'stop', 'marker', 'max_height', 'max_height_waveform', 'mode']]
                        st.dataframe(display_df)
                    else:
                        st.warning("No valid results found for this file.")
            else:
                st.info("No batch results to display. Process files in the sidebar.")

    with tab3:
        st.header("Waveform Boxes")

        def display_waveform_boxes(results):
            if not results:
                st.info("No data to display.")
                return

            # Determine number of columns, max 3
            num_results = len(results)
            num_cols = min(num_results, 3)
            if num_cols == 0: return

            cols = st.columns(num_cols)
            for i, result in enumerate(results):
                with cols[i % num_cols]:
                    with st.container():
                        st.markdown(f"**🔄 ITERATION_{result['iteration']:02d}**")
                        st.markdown(f"<p style='background-color:yellow;color:black;padding:3px;border-radius:3px;'>⏱️ Duration: {result['duration']:.3f} seconds</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='background-color:yellow;color:black;padding:3px;border-radius:3px;'>🎯 Selected: {result['max_height_waveform']}</p>", unsafe_allow_html=True)
                        st.code(f"🔢 {result['start']} → {result['stop']}")

                        with st.expander("📏 All Heights & Waveforms"):
                            for height_info in result['all_heights']:
                                is_selected = str(height_info['marker']) == str(result['marker'])
                                height_text = f"M{height_info['marker']}: {height_info['height']}px, {height_info['waveform']}"
                                if is_selected:
                                    st.markdown(f"**{height_text}**")
                                else:
                                    st.write(height_text)

                        # Copy button data preparation
                        height_waveform_data = []
                        for idx, height_info in enumerate(result['all_heights'], 1):
                            height = height_info['height']
                            waveform = height_info['waveform']
                            height_waveform_data.append(f"{idx}. Height - {height}, Waveform - {waveform}")
                        data_to_copy = "\\n".join(height_waveform_data)

                        st.download_button(
                            label="📋 Copy Data",
                            data=data_to_copy,
                            file_name=f"iteration_{result['iteration']}_waveforms.txt",
                            mime="text/plain",
                            key=f"copy_btn_{result['iteration']}"
                        )
                        st.markdown("---")


        if st.session_state.processing_mode == "Single Entry":
            display_waveform_boxes(st.session_state.results)
        else: # Batch Mode
            if st.session_state.batch_results:
                for filename, results in st.session_state.batch_results.items():
                    st.subheader(f"Waveforms for: {filename}")
                    display_waveform_boxes(results)
            else:
                st.info("No data to display.")

    with tab4:
        st.header("All Heights & Waveforms")

        def get_all_heights_df(results):
            all_heights_data = []
            for result in results:
                iteration_num = result['iteration']
                for height_info in result['all_heights']:
                    all_heights_data.append({
                        'Iteration': iteration_num,
                        'Marker': height_info['marker'],
                        'Height': height_info['height'],
                        'Waveform': height_info['waveform']
                    })
            return pd.DataFrame(all_heights_data)

        if st.session_state.processing_mode == "Single Entry":
            if st.session_state.results:
                heights_df = get_all_heights_df(st.session_state.results)
                st.dataframe(heights_df)
            else:
                st.info("No data to display.")
        else: # Batch Mode
            if st.session_state.batch_results:
                for filename, results in st.session_state.batch_results.items():
                    st.subheader(f"Heights & Waveforms for: {filename}")
                    if results:
                        heights_df = get_all_heights_df(results)
                        st.dataframe(heights_df)
                    else:
                        st.warning("No valid results found for this file.")
            else:
                st.info("No data to display.")

    with tab5:
        st.header("Batch Processing Results")
        if st.session_state.processing_mode == "Batch Files" and st.session_state.batch_results:
            st.write("This tab shows the raw results data for the processed batch.")
            st.json(st.session_state.batch_results)
        else:
            st.info("No batch results to display. Process files in batch mode to see results here.")

    with tab6:
        st.header("⚖️ Log Comparison")

        col1, col2 = st.columns(2)
        with col1:
            log_a = st.text_area("Log A (e.g., Previous Version)", height=300, key="log_a_input")
        with col2:
            log_b = st.text_area("Log B (e.g., Current Version)", height=300, key="log_b_input")

        if 'comparison_html' not in st.session_state:
            st.session_state.comparison_html = ""

        def generate_comparison_html(result_a, result_b):
            duration_a = result_a['duration']
            duration_b = result_b['duration']
            duration_diff = duration_b - duration_a

            if duration_a > 0:
                deviation = (duration_diff / duration_a) * 100
                verdict, color = ("Slower", "red") if duration_diff > 0 else ("Faster", "green")
                verdict_text = f"{verdict} ({deviation:+.2f}%)"
            else:
                verdict_text, color = "N/A", "black"

            html = f"""
            <h4>Comparison Summary</h4>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width:100%;">
                <tr style="background-color: #f0f0f0;">
                    <th>Metric</th><th>Log A (Previous)</th><th>Log B (Current)</th><th>Difference</th><th style="color: {color};">Deviation</th>
                </tr>
                <tr>
                    <td><b>Duration (s)</b></td><td>{duration_a:.3f}</td><td>{duration_b:.3f}</td><td>{duration_diff:+.3f}</td><td style="color: {color};"><b>{verdict_text}</b></td>
                </tr>
            </table>
            <h4>Waveform Pattern Comparison</h4>
            """

            seq_a = [(h['height'], h['waveform']) for h in result_a['all_heights']]
            seq_b = [(h['height'], h['waveform']) for h in result_b['all_heights']]

            table_html = """
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f0f0f0;">
                    <th>Step</th><th>Log A (Height, Waveform)</th><th>Log B (Height, Waveform)</th><th>Comparison</th>
                </tr>
            """

            matcher = difflib.SequenceMatcher(None, seq_a, seq_b)
            step = 1
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    for i in range(i1, i2):
                        table_html += f'<tr><td>{step}</td><td>{seq_a[i][0]}px, {seq_a[i][1]}</td><td>{seq_b[j1 + (i - i1)][0]}px, {seq_b[j1 + (i - i1)][1]}</td><td style="color: green;">Identical</td></tr>'
                        step += 1
                if tag == 'delete':
                    for i in range(i1, i2):
                        table_html += f'<tr style="background-color: #ffcccb;"><td>{step}</td><td>{seq_a[i][0]}px, {seq_a[i][1]}</td><td>-</td><td style="color: red;"><b>Removed from Log B</b></td></tr>'
                        step += 1
                if tag == 'insert':
                    for j in range(j1, j2):
                        table_html += f'<tr style="background-color: #ccffcc;"><td>{step}</td><td>-</td><td>{seq_b[j][0]}px, {seq_b[j][1]}</td><td style="color: blue;"><b>New in Log B</b></td></tr>'
                        step += 1
                if tag == 'replace':
                    for i, j in zip(range(i1, i2), range(j1, j2)):
                        table_html += f'<tr style="background-color: #ffffcc;"><td>{step}</td><td>{seq_a[i][0]}px, {seq_a[i][1]}</td><td>{seq_b[j][0]}px, {seq_b[j][1]}</td><td style="color: orange;"><b>Deviation</b></td></tr>'
                        step += 1

            table_html += "</table>"
            html += table_html
            return html

        if st.button("⚖️ Compare Logs", use_container_width=True):
            if log_a and log_b:
                with st.spinner("Comparing logs..."):
                    mode_map = {
                        "Default (Button Up)": "default", "Swipe (Button Down)": "swipe", "Suspend (Power Button)": "suspend"
                    }
                    current_mode = mode_map.get(st.session_state.calculation_mode, "default")

                    result_a = process_log_iteration_data(log_a.split('\\n'), "A", current_mode)
                    result_b = process_log_iteration_data(log_b.split('\\n'), "B", current_mode)

                    if result_a and result_b:
                        st.session_state.comparison_html = generate_comparison_html(result_a, result_b)
                    else:
                        st.session_state.comparison_html = "<p style='color:red;'>Could not process one or both logs. Please ensure they are valid single iterations.</p>"
            else:
                st.warning("Please paste log content into both Log A and Log B inputs.")

        st.markdown(st.session_state.comparison_html, unsafe_allow_html=True)
