from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QFileDialog, QTextEdit, QListWidget, 
                           QListWidgetItem, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, QThread
import sys
from .parse import parse_torrent_file
from .downloader import download
from .torrent_file import TorrentFile

class TorrentListItem(QWidget):
    def __init__(self, torrent_file, parent=None):
        super().__init__(parent)
        self.torrent_file = torrent_file
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Display torrent name - get it from the info object
        name = torrent_file.get_info().get_name() if torrent_file.get_info() else "Unknown"
        self.name_label = QLabel(name)
        layout.addWidget(self.name_label, stretch=1)
        
        # Download button for this torrent
        self.download_button = QPushButton("Download")
        self.download_button.setFixedWidth(100)
        layout.addWidget(self.download_button)
        
        self.setLayout(layout)

class DownloadThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, torrent_file):
        super().__init__()
        self.torrent_file = torrent_file

    def run(self):
        name = self.torrent_file.get_info().get_name() if self.torrent_file.get_info() else "Unknown"
        self.update_signal.emit(f"Starting download of {name}...")
        try:
            download(self.torrent_file, self.update_signal.emit)
        except Exception as e:
            self.update_signal.emit(f"Error starting download: {e}")

class FileSelectorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("tmbit_py")
        self.setGeometry(100, 100, 800, 600)
        
        # Main layout
        main_layout = QHBoxLayout()
        
        # Left side - Torrent list and add button
        left_panel = QVBoxLayout()
        
        # Add torrent button
        self.add_button = QPushButton("Add Torrent File")
        self.add_button.clicked.connect(self.open_file_dialog)
        left_panel.addWidget(self.add_button)
        
        # Torrent list
        self.torrent_list = QListWidget()
        self.torrent_list.setMinimumWidth(300)
        left_panel.addWidget(self.torrent_list)
        
        # Add left panel to main layout
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        main_layout.addWidget(left_widget)
        
        # Vertical separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Right side - Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        main_layout.addWidget(self.output_display)
        
        # Set the main layout
        self.setLayout(main_layout)
        
        # Initialize download threads dict
        self.download_threads = {}

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Torrent File", "", "Torrent Files (*.torrent)")
        
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
        
        # Connect download button
        item_widget.download_button.clicked.connect(
            lambda: self.start_download(torrent_file)
        )
        
        # Create list item and set widget
        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())
        self.torrent_list.addItem(list_item)
        self.torrent_list.setItemWidget(list_item, item_widget)

    def start_download(self, torrent_file):
        # Get torrent name for thread tracking
        name = torrent_file.get_info().get_name() if torrent_file.get_info() else "Unknown"
        
        # Create and start download thread
        thread = DownloadThread(torrent_file)
        thread.update_signal.connect(self.output_display.append)
        thread.start()
        
        # Store thread reference
        self.download_threads[name] = thread

# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Apply dark theme
    dark_stylesheet = """
        QWidget {
            background-color: #2E2E2E;
            color: #FFFFFF;
        }
        QPushButton {
            background-color: #4C4C4C;
            color: #FFFFFF;
            border: 1px solid #3E3E3E;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #5C5C5C;
        }
        QTextEdit, QListWidget {
            background-color: #3E3E3E;
            color: #FFFFFF;
            border: 1px solid #5E5E5E;
        }
        QFrame[frameShape="5"] { /* VLine */
            background-color: #5E5E5E;
            width: 1px;
        }
    """
    app.setStyleSheet(dark_stylesheet)

    window = FileSelectorApp()
    window.show()
    sys.exit(app.exec_())