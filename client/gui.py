from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QFileDialog, QTextEdit, QListWidget, 
                           QListWidgetItem, QLabel, QFrame, QProgressBar)
from PyQt5.QtCore import pyqtSignal, QThread, Qt
import sys
from client.parse import parse_torrent_file
from client.downloader import download

class DownloadThread(QThread):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    completed_signal = pyqtSignal(bool)
    
    def __init__(self, torrent_file):
        super().__init__()
        self.torrent_file = torrent_file
        
        # Add debug logging
        pieces = self.torrent_file.get_info().get_pieces()
        piece_count = len(pieces) if pieces else 0
        print(f"Debug - Total pieces: {piece_count}")
        print(f"Debug - Pieces data: {pieces[:10]}...")  # Print first 10 pieces
        
        self.total_pieces = piece_count
        self.current_piece = 0
        self.is_complete = False
        
        # Verify the piece count is non-zero
        if self.total_pieces == 0:
            print("Warning: Zero pieces detected in torrent file")
            # You might want to raise an exception here
        
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
                    self.completed_signal.emit(True)  # Success
                    return
                
                self.update_signal.emit(message)
            
            download(self.torrent_file, progress_callback)
            
        except Exception as e:
            error_msg = f"Error during download: {e}"
            self.update_signal.emit(error_msg)
            self.completed_signal.emit(False)  # Failure


class TorrentListItem(QWidget):
    def __init__(self, torrent_file, parent=None):
        super().__init__(parent)
        self.torrent_file = torrent_file
        
        # Main layout with more padding
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # Increased margins
        layout.setSpacing(12)  # Increased spacing between elements
        
        # Top section with name and size
        top_section = QVBoxLayout()
        top_section.setSpacing(8)  # Increased spacing
        
        # Torrent name with larger, bold font
        name = torrent_file.get_info().get_name() if torrent_file.get_info() else "Unknown"
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumHeight(20)  # Minimum height for name
        top_section.addWidget(self.name_label)
        
        # Size information
        try:
            size = torrent_file.get_info().get_piece_length()
            size_text = f"Size: {size} bytes"
            if float(size) / 1024 > 0.1:
                size_text = f"Size: {size / 1024:.2f} KB"
            if float(size) / (1024 * 1024) > 0.1:
                size_text = f"Size: {size / (1024 * 1024):.2f} MB"
        except:
            size = torrent_file.get_length() // (1024 * 1024)
            size_text = f"Size: Unknown"
        
        self.size_label = QLabel(size_text)
        self.size_label.setStyleSheet("color: #888888; font-size: 12px;")
        self.size_label.setMinimumHeight(15)  # Minimum height for size
        top_section.addWidget(self.size_label)
        
        layout.addLayout(top_section)
        
        # Progress section
        progress_section = QVBoxLayout()
        progress_section.setSpacing(8)  # Increased spacing
        
        # Progress bar with increased height
        # Progress bar with proper initialization
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m pieces")
        # Initialize with actual piece count
        total_pieces = len(torrent_file.get_info().get_pieces())
        self.progress_bar.setMaximum(total_pieces)
        self.progress_bar.setValue(0)
        # Add debug logging
        print(f"Debug - Progress bar initialized with {total_pieces} pieces")
        
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #5E5E5E;
                border-radius: 5px;
                text-align: center;
                background-color: #3E3E3E;
                font-size: 12px;
                margin-top: 5px;
                margin-bottom: 5px;
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
        status_section.setSpacing(10)  # Increased spacing
        
        # Download speed
        self.speed_label = QLabel("Speed: --")
        self.speed_label.setStyleSheet("color: #888888;")
        self.speed_label.setMinimumHeight(15)  # Minimum height
        status_section.addWidget(self.speed_label)
        
        # Spacer
        status_section.addStretch()
        
        # ETA
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setStyleSheet("color: #888888;")
        self.eta_label.setMinimumHeight(15)  # Minimum height
        status_section.addWidget(self.eta_label)
        
        progress_section.addLayout(status_section)
        
        # Status message
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #AAAAAA;
                font-size: 12px;
                padding: 4px;
                min-height: 20px;
            }
        """)
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        progress_section.addWidget(self.status_label)
        
        layout.addLayout(progress_section)
        
        # Bottom section with buttons
        button_section = QHBoxLayout()
        button_section.setContentsMargins(0, 10, 0, 10)  # Added vertical margins
        
        # Download button with improved styling
        self.download_button = QPushButton("Download")
        self.download_button.setMinimumWidth(120)
        self.download_button.setMinimumHeight(35)  # Increased height
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #2E2E2E;
                color: #666666;
            }
            QPushButton[error="true"] {
                background-color: #f44336;
            }
            QPushButton[error="true"]:hover {
                background-color: #da190b;
            }
        """)
        button_section.addStretch()
        button_section.addWidget(self.download_button)
        
        layout.addLayout(button_section)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            QFrame {
                background-color: #5E5E5E;
                margin-top: 10px;
            }
        """)
        layout.addWidget(separator)
        
        self.setLayout(layout)
        
        # Set a fixed minimum height for consistent appearance
        self.setMinimumHeight(250)  # Increased minimum height

    def start_download(self):
        """Called when download starts"""
        self.download_button.setEnabled(False)
        self.download_button.setText("Downloading...")
        self.download_button.setProperty("error", False)
        self.progress_bar.show()
        self.status_label.show()
        self.progress_bar.setValue(0)
    
    def mark_error(self, error_message):
        """Called when download encounters an error"""
        self.download_button.setEnabled(True)
        self.download_button.setText("Retry Download")
        self.download_button.setProperty("error", True)
        self.download_button.style().unpolish(self.download_button)
        self.download_button.style().polish(self.download_button)
        self.status_label.setText(error_message)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #f44336;
                font-size: 12px;
                padding: 4px;
                min-height: 20px;
            }
        """)
        self.speed_label.setText("Speed: --")
        self.eta_label.setText("ETA: --")
        
    def update_status(self, message):
        """Update status message and labels"""
        self.status_label.setText(message)
        
        # Update speed if the message contains speed information
        if "Speed:" in message:
            self.speed_label.setText(message)
        # Update ETA if the message contains ETA information
        elif "ETA:" in message:
            self.eta_label.setText(message)
            
    def update_progress(self, current, total):
        """Update progress bar"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        
    def mark_complete(self):
        """Called when download completes"""
        self.download_button.setText("Download Complete")
        self.download_button.setEnabled(False)
        self.status_label.setText("Download completed successfully!")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.speed_label.setText("Speed: 0 KB/s")
        self.eta_label.setText("ETA: Complete")

class FileSelectorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("tmbit_py")
        self.setGeometry(100, 100, 1000, 800)
        
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        
        # Left side - Torrent list and add button
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)  # Increased spacing
        
        # Header section
        header = QVBoxLayout()
        header.setSpacing(10)  # Increased spacing
        
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
        self.torrent_list.setMinimumWidth(400)
        self.torrent_list.setSpacing(15)  # Add spacing between items
        self.torrent_list.setStyleSheet("""
            QListWidget {
                background-color: #2E2E2E;
                border: 1px solid #5E5E5E;
                border-radius: 4px;
                padding: 10px;
            }
            QListWidget::item {
                padding: 5px;
                margin-bottom: 10px;  /* Add margin between items */
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
        self.active_downloads = set()
        self.download_threads = {}
        
        # Add flag to track if a download is in progress
        self.download_in_progress = False
        
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
        
        # Add to active downloads
        self.active_downloads.add(name)
        
        # Create and configure download thread
        thread = DownloadThread(torrent_file)
        thread.update_signal.connect(self.output_display.append)
        thread.update_signal.connect(item_widget.update_status)
        thread.progress_signal.connect(item_widget.update_progress)
        thread.completed_signal.connect(lambda success: self.handle_download_complete(name, success, item_widget))
        thread.start()
        
        # Update UI
        item_widget.start_download()
        self.download_threads[name] = thread
        
        # Update download button states
        self.update_download_buttons()
    
    def handle_download_complete(self, name, success, item_widget):
        """Handle both successful and failed downloads"""
        # Remove from active downloads
        self.active_downloads.remove(name)
        
        if success:
            item_widget.mark_complete()
            self.output_display.append(f"Download completed successfully: {name}")
        else:
            item_widget.mark_error("Download failed. Click 'Retry Download' to try again.")
            self.output_display.append(f"Download failed: {name}")
        
        # Clean up thread
        if name in self.download_threads:
            self.download_threads[name].deleteLater()
            del self.download_threads[name]
        
        # Update download button states
        self.update_download_buttons()
    
    def update_download_buttons(self):
        """Update the state of all download buttons based on active downloads"""
        max_concurrent_downloads = 1  # You can adjust this number for multiple concurrent downloads
        
        for i in range(self.torrent_list.count()):
            list_item = self.torrent_list.item(i)
            widget = self.torrent_list.itemWidget(list_item)
            
            # Skip if this widget is already downloading or completed
            if widget.download_button.text() in ["Downloading...", "Download Complete"]:
                continue
            
            # Enable/disable based on number of active downloads
            can_download = len(self.active_downloads) < max_concurrent_downloads
            widget.download_button.setEnabled(can_download)
            
            if not can_download and not widget.download_button.property("error"):
                widget.download_button.setStyleSheet("""
                    QPushButton {
                        background-color: #2E2E2E;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 13px;
                        color: #666666;
                    }
                """)

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