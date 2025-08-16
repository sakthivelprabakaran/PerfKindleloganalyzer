
"""
PDF Export Module for Kindle Log Analyzer
Generates comprehensive PDF reports with highlighted start/stop points
"""
import re
import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import yellow, black, white, blue, red, green
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


class PdfExporter:
    """PDF export functionality with highlighting and comprehensive reporting"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        """Setup custom paragraph styles for the PDF"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            textColor=blue,
            alignment=TA_CENTER
        )

        # Iteration header style
        self.iteration_style = ParagraphStyle(
            'IterationHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=red,
            borderWidth=1,
            borderColor=red,
            borderPadding=5
        )

        # Log line style
        self.log_style = ParagraphStyle(
            'LogLine',
            parent=self.styles['Code'],
            fontSize=8,
            fontName='Courier',
            leftIndent=10,
            spaceAfter=2
        )

        # Highlighted log style
        self.highlight_style = ParagraphStyle(
            'HighlightedLog',
            parent=self.log_style,
            backColor=yellow,
            borderColor=red,
            borderWidth=0.5
        )

        # Summary style
        self.summary_style = ParagraphStyle(
            'Summary',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            spaceAfter=8,
            textColor=blue
        )

    def highlight_log_line(self, line, result):
        """Apply highlighting to log lines for start/stop points"""
        highlighted_line = line

        if line == result.get('start_line'):
            highlighted_line = f'<font backColor="yellow">{line}</font>'
        elif line == result.get('stop_line'):
            highlighted_line = f'<font backColor="yellow">{line}</font>'
        elif line == result.get('height_line'):
            highlighted_line = f'<font backColor="yellow">{line}</font>'

        return highlighted_line

    def generate_pdf_report(self, results, output_path, mode="default"):
        """Generate comprehensive PDF report with highlighting"""
        try:
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50
            )

            story = []

            # Add title
            title = f"Kindle Log Analysis Report - {mode.title()} Mode"
            story.append(Paragraph(title, self.title_style))
            story.append(Spacer(1, 20))

            # Add generation timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            story.append(Paragraph(f"Generated on: {timestamp}", self.styles['Normal']))
            story.append(Spacer(1, 20))

            # Generate table of contents with durations and averages
            story.extend(self.create_table_of_contents(results))
            story.append(PageBreak())

            # Process each iteration
            for idx, result in enumerate(results):
                story.extend(self.process_iteration_for_pdf(result))
                if idx < len(results) - 1:  # Add page break between iterations
                    story.append(PageBreak())

            # Build PDF
            doc.build(story)
            return True, f"PDF report generated successfully at {output_path}"

        except Exception as e:
            return False, f"Error generating PDF: {str(e)}"

    def export_pdf_report(self, results, output_path, current_mode):
        """Export a single PDF report."""
        try:
            self.generate_pdf_report(results, output_path, current_mode)
            return True, f"Report successfully exported to {output_path}"
        except Exception as e:
            return False, f"Failed to create PDF file: {e}"

    def export_zip_report(self, batch_results, zip_path, current_mode):
        """Export all reports into a single ZIP file."""
        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for filename, results in batch_results.items():
                    # Generate PDF report
                    pdf_path = f"{Path(filename).stem}_report.pdf"
                    self.generate_pdf_report(results, pdf_path, current_mode)
                    zipf.write(pdf_path, os.path.basename(pdf_path))
                    os.remove(pdf_path)

            return True, f"Reports successfully exported to {zip_path}"

        except Exception as e:
            return False, f"Failed to create ZIP file: {e}"

    def create_table_of_contents(self, results):
        """Create table of contents with iteration summary"""
        story = []

        # Table of contents header
        story.append(Paragraph("Table of Contents", self.styles['Heading1']))
        story.append(Spacer(1, 15))

        # Summary statistics
        if results:
            total_iterations = len(results)
            durations = [r.get('duration', 0) for r in results if r.get('duration') is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0
            min_duration = min(durations) if durations else 0
            max_duration = max(durations) if durations else 0

            summary_data = [
                ['Metric', 'Value'],
                ['Total Iterations', str(total_iterations)],
                ['Average Duration', f"{avg_duration:.2f}"],
                ['Min Duration', str(min_duration)],
                ['Max Duration', str(max_duration)]
            ]

            summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), white),
                ('GRID', (0, 0), (-1, -1), 1, black)
            ]))

            story.append(summary_table)
            story.append(Spacer(1, 20))

        # Detailed iteration table
        if results:
            table_data = [['Iteration', 'Start', 'Stop', 'Duration', 'Max Height', 'Waveform']]

            for result in results:
                table_data.append([
                    f"ITERATION_{result.get('iteration', 'N/A')}",
                    str(result.get('start', 'N/A')),
                    str(result.get('stop', 'N/A')),
                    str(result.get('duration', 'N/A')),
                    str(result.get('max_height', 'N/A')),
                    result.get('max_height_waveform', 'N/A')
                ])

            iterations_table = Table(table_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.2*inch])
            iterations_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), green),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), white),
                ('GRID', (0, 0), (-1, -1), 1, black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, '#f0f0f0'])
            ]))

            story.append(iterations_table)

        return story

    def process_iteration_for_pdf(self, result):
        """Process a single iteration for PDF output"""
        story = []

        # Iteration header
        iteration_num = result.get('iteration', 'Unknown')
        story.append(Paragraph(f"ITERATION_{iteration_num}", self.iteration_style))
        story.append(Spacer(1, 10))

        # Process original log content with highlighting
        original_log = result.get('original_log', '')
        if original_log:
            story.append(Paragraph("Original Log Content:", self.styles['Heading3']))
            story.append(Spacer(1, 5))

            # Split log into lines and process each
            log_lines = original_log.split('\n')
            for line in log_lines:
                if line.strip():
                    highlighted_line = self.highlight_log_line(line.strip(), result)
                    # Escape HTML characters for ReportLab
                    safe_line = highlighted_line.replace('<', '&lt;').replace('>', '&gt;')
                    # But keep our highlighting tags
                    safe_line = re.sub(r'&lt;(/?font[^&]*?)&gt;', r'<\1>', safe_line)
                    safe_line = re.sub(r'&lt;(/?b)&gt;', r'<\1>', safe_line)

                    story.append(Paragraph(safe_line, self.log_style))

            story.append(Spacer(1, 15))

        # Add calculation details
        story.extend(self.create_calculation_details(result))

        return story

    def create_calculation_details(self, result):
        """Create calculation details section for an iteration"""
        story = []

        story.append(Paragraph("Calculation Details:", self.styles['Heading3']))
        story.append(Spacer(1, 5))

        # Key metrics
        details = [
            f"<b>Start Time:</b> {result.get('start', 'N/A')}",
            f"<b>Stop Time:</b> {result.get('stop', 'N/A')}",
            f"<b>Duration:</b> {result.get('duration', 'N/A')}",
            f"<b>Selected Marker:</b> {result.get('marker', 'N/A')}",
            f"<b>Max Height:</b> {result.get('max_height', 'N/A')}",
            f"<b>Max Height Waveform:</b> {result.get('max_height_waveform', 'N/A')}"
        ]

        for detail in details:
            story.append(Paragraph(detail, self.summary_style))

        # All heights information
        all_heights = result.get('all_heights', [])
        if all_heights:
            story.append(Spacer(1, 10))
            story.append(Paragraph("All Heights Found:", self.styles['Heading4']))

            height_data = [['Marker', 'Height', 'Waveform']]
            for height_info in all_heights:
                height_data.append([
                    height_info.get('marker', 'N/A'),
                    str(height_info.get('height', 'N/A')),
                    height_info.get('waveform', 'N/A')
                ])

            if len(height_data) > 1:  # More than just header
                height_table = Table(height_data, colWidths=[1*inch, 1*inch, 2*inch])
                height_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), blue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), white),
                    ('GRID', (0, 0), (-1, -1), 1, black)
                ]))

                story.append(height_table)

        story.append(Spacer(1, 15))
        return story


def test_pdf_export():
    """Test function for PDF export"""
    # Sample test data
    test_results = [
        {
            'iteration': '01',
            'start': 650205,
            'stop': 651234,
            'duration': 1029,
            'marker': '123',
            'max_height': 1200,
            'max_height_waveform': 'DU',
            'all_heights': [
                {'marker': '123', 'height': 1200, 'waveform': 'DU'},
                {'marker': '124', 'height': 800, 'waveform': 'unknown'}
            ],
            'original_log': '''1751099650.205215 def:pbpress:time=650.205:Power button pressed
1751099651.234567 update end marker=123 end time=1751099651234567'''
        }
    ]

    exporter = PdfExporter()
    success, message = exporter.generate_pdf_report(
        test_results,
        "/home/ubuntu/test_report.pdf",
        "suspend"
    )

    print(f"PDF Export Test: {message}")
    return success


if __name__ == "__main__":
    test_pdf_export()
