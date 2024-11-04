from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QFileDialog, QTextEdit, QListWidget, 
                           QListWidgetItem, QLabel, QFrame, QProgressBar)
from PyQt5.QtCore import pyqtSignal, QThread, Qt
import sys
from client.parse import parse_torrent_file
from client.downloader import download

class DownloadThread(QThread):
    update_signal = pyqtSignal(str)  # For text updates
    progress_signal = pyqtSignal(int, int)  # For progress updates (current, total)
    completed_signal = pyqtSignal()  # New signal for download completion

    def __init__(self, torrent_file):
        super().__init__()
        self.torrent_file = torrent_file
        self.current_piece = 0
        self.total_pieces = len(torrent_file.get_info().get_pieces())
        self.is_complete = False

    def run(self):
        name = self.torrent_file.get_info().get_name() if self.torrent_file.get_info() else "Unknown"
        self.update_signal.emit(f"Starting download of {name}...")
        try:
            def progress_callback(message):
                if self.is_complete:  # Skip if already complete
                    return
                
                if message.startswith("Downloading piece"):
                    self.current_piece += 1
                    self.progress_signal.emit(self.current_piece, self.total_pieces)
                elif message == "Download complete":
                    self.is_complete = True
                    self.completed_signal.emit()
                    return  # Exit callback after completion
                
                self.update_signal.emit(message)
            
            download(self.torrent_file, progress_callback)
            
        except Exception as e:
            self.update_signal.emit(f"Error during download: {e}")

class TorrentListItem(QWidget):
    def __init__(self, torrent_file, parent=None):
        super().__init__(parent)
        self.torrent_file = torrent_file
        
        # Main layout with more padding
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)  # Increased spacing between elements
        
        # Top section with name and size
        top_section = QVBoxLayout()
        
        # Torrent name with larger, bold font
        name = torrent_file.get_info().get_name() if torrent_file.get_info() else "Unknown"
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.name_label.setWordWrap(True)  # Allow long names to wrap
        top_section.addWidget(self.name_label)
        
        # Size information
        try:
            size = torrent_file.get_info().get_piece_length()
            size_text = f"Size: {size} bytes"
            if float(size) / 1024 > 0.1:
                size_text = f"Size: {size / 1024} kb"
            if float(size) / (1024 * 1024) > 0.1:
                size_text = f"Size: {size / (1024 * 1024)} mb"

        except:
            size = torrent_file.get_length() // (1024 * 1024)  # Convert to MB
            size_text = f"Size: Unknown"
        
        self.size_label = QLabel(size_text)
        self.size_label.setStyleSheet("color: #888888; font-size: 12px;")
        top_section.addWidget(self.size_label)
        
        layout.addLayout(top_section)
        
        # Progress section
        progress_section = QVBoxLayout()
        progress_section.setSpacing(4)
        
        # Progress bar with increased height
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m pieces")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #5E5E5E;
                border-radius: 5px;
                text-align: center;
                background-color: #3E3E3E;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()
        progress_section.addWidget(self.progress_bar)
        
        # Status section with detailed information
        status_section = QHBoxLayout()
        
        # Download speed
        self.speed_label = QLabel("Speed: --")
        self.speed_label.setStyleSheet("color: #888888;")
        status_section.addWidget(self.speed_label)
        
        # Spacer
        status_section.addStretch()
        
        # ETA
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setStyleSheet("color: #888888;")
        status_section.addWidget(self.eta_label)
        
        progress_section.addLayout(status_section)
        
        # Status message
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #AAAAAA;
                font-size: 12px;
                padding: 4px;
            }
        """)
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        progress_section.addWidget(self.status_label)
        
        layout.addLayout(progress_section)
        
        # Bottom section with buttons
        button_section = QHBoxLayout()
        
        # Download button with improved styling
        self.download_button = QPushButton("Download")
        self.download_button.setMinimumWidth(120)
        self.download_button.setMinimumHeight(30)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #2E2E2E;
                color: #666666;
            }
        """)
        button_section.addStretch()
        button_section.addWidget(self.download_button)
        
        layout.addLayout(button_section)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #5E5E5E;")
        layout.addWidget(separator)
        
        self.setLayout(layout)
        
        # Set a fixed minimum height for consistent appearance
        self.setMinimumHeight(200)
    
    def update_progress(self, current, total):
        self.progress_bar.show()
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        
        # Update completion percentage
        percentage = (current / total) * 100 if total > 0 else 0
        self.speed_label.setText(f"Speed: {self._format_speed(1024*1024)}")  # Example speed
        self.eta_label.setText(f"ETA: {self._format_eta(percentage)}")
    
    def update_status(self, status):
        self.status_label.show()
        self.status_label.setText(status)
        
    def mark_complete(self):
        self.download_button.setEnabled(False)
        self.download_button.setText("Download Complete")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #45a049;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:disabled {
                background-color: #45a049;
                color: #FFFFFF;
            }
        """)
        
    def start_download(self):
        self.download_button.setEnabled(False)
        self.download_button.setText("Downloading...")
        self.progress_bar.show()
        self.status_label.show()
        self.speed_label.show()
        self.eta_label.show()
    
    def _format_speed(self, bytes_per_sec):
        if bytes_per_sec >= 1024*1024:
            return f"{bytes_per_sec/(1024*1024):.1f} MB/s"
        elif bytes_per_sec >= 1024:
            return f"{bytes_per_sec/1024:.1f} KB/s"
        return f"{bytes_per_sec:.1f} B/s"
    
    def _format_eta(self, percentage):
        if percentage < 100:
            remaining_seconds = (100 - percentage) * 60  # Example calculation
            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return "Complete"

class FileSelectorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("tmbit_py")
        self.setGeometry(100, 100, 1000, 800)  # Increased window size
        
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)  # Increased spacing between panels
        
        # Left side - Torrent list and add button
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)  # Increased spacing between elements
        
        # Header section
        header = QVBoxLayout()
        
        # Title
        title = QLabel("Torrent Downloads")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        header.addWidget(title)
        
        # Add torrent button with improved styling
        self.add_button = QPushButton("Add Torrent File")
        self.add_button.setMinimumHeight(40)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.add_button.clicked.connect(self.open_file_dialog)
        header.addWidget(self.add_button)
        
        left_panel.addLayout(header)
        
        # Torrent list with improved styling
        self.torrent_list = QListWidget()
        self.torrent_list.setMinimumWidth(400)  # Increased width
        self.torrent_list.setStyleSheet("""
            QListWidget {
                background-color: #2E2E2E;
                border: 1px solid #5E5E5E;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #404040;
            }
        """)
        left_panel.addWidget(self.torrent_list)
        
        # Add left panel to main layout
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        main_layout.addWidget(left_widget)
        
        # Vertical separator with improved styling
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #5E5E5E;")
        main_layout.addWidget(separator)
        
        # Right side - Output display with improved styling
        right_panel = QVBoxLayout()
        
        # Log title
        log_title = QLabel("Download Log")
        log_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        right_panel.addWidget(log_title)
        
        # Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setStyleSheet("""
            QTextEdit {
                background-color: #2E2E2E;
                border: 1px solid #5E5E5E;
                border-radius: 4px;
                padding: 10px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        right_panel.addWidget(self.output_display)
        
        # Add right panel to main layout
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        main_layout.addWidget(right_widget)
        
        # Set the main layout
        self.setLayout(main_layout)
        
        # Initialize download threads dict
        self.download_threads = {}
        
        # Set the ratio between left and right panels (60:40)
        main_layout.setStretch(0, 60)
        main_layout.setStretch(2, 40)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Torrent File",
            "",
            "Torrent Files (*.torrent)"
        )
        
        if file_path:
            try:
                torrent_file = parse_torrent_file(file_path)
                self.add_torrent_to_list(torrent_file)
                name = torrent_file.get_info().get_name() if torrent_file.get_info() else "Unknown"
                self.output_display.append(f"Added torrent: {name}")
            except Exception as e:
                self.output_display.append(f"Error parsing torrent: {e}")

    def add_torrent_to_list(self, torrent_file):
        # Create list item widget
        item_widget = TorrentListItem(torrent_file)
        
        # Create list item and set widget
        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())
        self.torrent_list.addItem(list_item)
        self.torrent_list.setItemWidget(list_item, item_widget)
        
        # Connect download button
        item_widget.download_button.clicked.connect(
            lambda: self.start_download(torrent_file, item_widget)
        )
        
        return item_widget

    def start_download(self, torrent_file, item_widget):
        name = torrent_file.get_info().get_name() if torrent_file.get_info() else "Unknown"
        
        thread = DownloadThread(torrent_file)
        thread.update_signal.connect(self.output_display.append)
        thread.update_signal.connect(item_widget.update_status)
        thread.progress_signal.connect(item_widget.update_progress)
        thread.completed_signal.connect(item_widget.mark_complete)  # Connect the completion signal
        thread.start()
        
        item_widget.start_download()
        self.download_threads[name] = thread

def main():
    app = QApplication(sys.argv)

    # Apply dark theme
    dark_stylesheet = """
        QWidget {
            background-color: #2E2E2E;
            color: #FFFFFF;
        }
    """
    app.setStyleSheet(dark_stylesheet)

    window = FileSelectorApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()