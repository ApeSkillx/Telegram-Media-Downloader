# Import necessary libraries
import concurrent.futures
from telethon import connection
from telethon.sessions import MemorySession
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from telethon.tl.types import DocumentAttributeFilename, DocumentAttributeVideo
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# Import PyQt5 widgets for GUI
from PyQt5.QtWidgets import (QLabel, QInputDialog, QScrollArea, QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QWidget, QListWidget, QMessageBox, QLineEdit,
    QInputDialog, QDialog, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QStyle, QStyleOptionButton, QAbstractItemView, QFileDialog)

# Import PyQt5 core components for threading and signals
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
# Additional utility imports
import cryptg # For faster downloads
import sys
import os
import asyncio
import time
import humanize # For human-readable file sizes
import datetime
from typing import List, Dict

class FileListWidget(QTableWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.files_data = {}  # Dictionary to store file information

    def init_ui(self):
        # Define table columns
        columns = ["", "Type", "Name", "Size", "Date", "Format", "Duration"]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Configure column sizes and behavior
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 30) # Checkbox column
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.setColumnWidth(1, 60) # Type column
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(3, 100) # Size column
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.setColumnWidth(4, 150)  # Date column
        self.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.setColumnWidth(5, 80)  # Format column

    def add_file(self, message_id: int, file_type: str, name: str, size: int, date: datetime.datetime, format_type: str,duration=None):
        """
        Add a new file to the table
        """
        row_position = self.rowCount()
        self.insertRow(row_position)
        
        # Create checkbox for file selection       
        checkbox = QTableWidgetItem()
        checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        checkbox.setCheckState(Qt.Unchecked)
        self.setItem(row_position, 0, checkbox) 

        # Add file information to table       
        self.setItem(row_position, 1, QTableWidgetItem(file_type))
        self.setItem(row_position, 2, QTableWidgetItem(name))
        self.setItem(row_position, 3, QTableWidgetItem(humanize.naturalsize(size)))
        self.setItem(row_position, 4, QTableWidgetItem(date.strftime("%d-%m-%Y")))  # Updated date format
        self.setItem(row_position, 5, QTableWidgetItem(format_type))
        self.setItem(row_position, 6, QTableWidgetItem(str(datetime.timedelta(seconds=duration)) if duration else "N/A"))  # Video duration
       
        # Store file data for later use    
        self.files_data[row_position] = {
            'message_id': message_id,
            'name': name,
            'size': size,
            'type': file_type,
            'format': format_type,
            'duration': duration
        }

    def get_selected_files(self) -> List[Dict]:
        
        """
        Return a list of selected files' information
        """
        selected_files = []
        for row in range(self.rowCount()):
            if self.item(row, 0).checkState() == Qt.Checked:
                selected_files.append(self.files_data[row])
        return selected_files

class DownloadProgressWidget(QWidget):
    """
    Widget to display download progress for individual files
    Shows file name, size, download speed, and estimated time remaining
    """

    def __init__(self, file_info):
        super().__init__()
        self.file_info = file_info
        self.init_ui()
        self.downloaded_size = 0
        self.start_time = None

    def init_ui(self):
        #Initialize the UI components for download progress displa
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create horizontal layout for file information
        info_layout = QHBoxLayout()

        # Setup name and size display        
        name_size_layout = QHBoxLayout()
        self.name_label = QLabel(self.file_info['name'])
        self.name_label.setMaximumWidth(300)
        self.name_label.setMinimumWidth(200)
        name_size_layout.addWidget(self.name_label)
        
        # Display file size
        self.size_label = QLabel(humanize.naturalsize(self.file_info['size']))
        self.size_label.setMinimumWidth(100)
        name_size_layout.addWidget(self.size_label)
        info_layout.addLayout(name_size_layout)

        # Setup download speed and time remaining display        
        status_layout = QHBoxLayout()
        self.speed_label = QLabel("0 B/s")
        self.speed_label.setMinimumWidth(100)
        status_layout.addWidget(self.speed_label)
        
        self.time_label = QLabel("--:--")
        self.time_label.setMinimumWidth(100)
        status_layout.addWidget(self.time_label)
        info_layout.addLayout(status_layout)
        
        layout.addLayout(info_layout)

        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        """
        Update the progress display with current download status
        Args:
            bytes_downloaded: Number of bytes downloaded so far
        """
        
    # Initialize start time on first update
    def update_progress(self, bytes_downloaded):
        if not self.start_time:
            self.start_time = time.time()

        self.downloaded_size = bytes_downloaded
        # Calculate and update progress percentage
        progress = int((bytes_downloaded / self.file_info['size']) * 100)
        self.progress_bar.setValue(progress)

        # Calculate and update download speed
        elapsed_time = time.time() - self.start_time
        speed = bytes_downloaded / elapsed_time if elapsed_time > 0 else 0
        self.speed_label.setText(f"{humanize.naturalsize(speed)}/s")

        # Calculate and update estimated time remaining
        if speed > 0:
            remaining_bytes = self.file_info['size'] - bytes_downloaded
            remaining_time = remaining_bytes / speed
            self.time_label.setText(str(datetime.timedelta(seconds=int(remaining_time))))

class AuthDialog(QDialog):
    
    """
    Dialog for Telegram authentication
    Allows users to enter either phone number or bot token
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telegram Authentication")
        self.layout = QFormLayout()
        self.setLayout(self.layout)

        # Phone number input
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number (e.g., +14155552671)")
        self.layout.addRow("Phone Number:", self.phone_input)

        # Separator
        self.layout.addRow(QLabel("-- OR --"))

        # Bot token input
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter bot token (e.g., 123456789:ABCdef...)")
        self.layout.addRow("Bot Token:", self.token_input)

        # Add OK and Cancel buttons
        buttons = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        buttons.addWidget(self.ok_button)
        buttons.addWidget(self.cancel_button)
        self.layout.addRow(buttons)

        # Connect button signals
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

class MessageScannerThread(QThread):    
    """
    Thread for scanning messages in a Telegram channel
    Emits signals for progress updates and found messages
    """
    # Define signals for communication with main threa
    progress_updated = pyqtSignal(int)
    message_found = pyqtSignal(dict)
    scan_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, api_id, api_hash, channel_link, phone_or_token):
        super().__init__()
        self.api_id = api_id
        self.api_hash = api_hash
        self.channel_link = channel_link
        self.phone_or_token = phone_or_token
        self.is_running = True

    def get_file_info(self, message):
        """
        Extract file information from a Telegram message
        Args:
            message: Telegram message object
        Returns:
            dict: File information including type, name, size, etc.
        """
        try:
            # Initialize default values
            file_type = "Unknown"
            file_name = f"file_{message.id}"
            file_size = 0
            file_format = "unknown"
            video_duration = None 

            # Handle document type messages (files, videos, etc.)
            if isinstance(message.media, MessageMediaDocument):
                file_size = message.media.document.size
                
                # Extract file information from document attributes
                for attr in message.media.document.attributes:
                    if isinstance(attr, DocumentAttributeFilename):
                        # Get filename from attribute
                        file_name = attr.file_name
                        break
                    elif isinstance(attr, DocumentAttributeVideo):
                        # Handle video files
                        file_name = f"video_{message.id}.mp4"
                        file_type = "Video"
                        video_duration = attr.duration  # Fetch video duration

                        break
                
                # Set file type based on mime type if not already set
                if file_type == "Unknown":
                    file_type = "Document"
                
                if hasattr(message.media.document, 'mime_type'):
                    mime_type = message.media.document.mime_type
                    if 'video' in mime_type:
                        file_type = "Video"
                    elif 'audio' in mime_type:
                        file_type = "Audio"
                    elif 'image' in mime_type:
                        file_type = "Image"

                # Get format from filename
                if '.' in file_name:
                    file_format = file_name.split('.')[-1].lower()
            
            # Handle photo type messages
            elif isinstance(message.media, MessageMediaPhoto):
                file_type = "Photo"
                file_name = f"photo_{message.id}.jpg"
                # Get the size of the largest photo version
                file_size = max((size.size for size in message.media.photo.sizes), default=0)
                file_format = "jpg"

            # Return compiled file information
            return {
                'message_id': message.id,
                'type': file_type,
                'name': file_name,
                'size': file_size,
                'date': message.date,
                'format': file_format,
                'duration': video_duration
            }
        except Exception as e:
            print(f"Error processing message {message.id}: {str(e)}")
            return None

    async def scan_messages(self):
        """
        Scan messages in the Telegram channel asynchronously
        """
        try:
            # Configure client settings for optimal performance
            client_config = {
                'connection': connection.ConnectionTcpFull,
                'use_ipv6': False,
                'timeout': 60,
                'connection_retries': 3,
                'retry_delay': 0,
                'auto_reconnect': True
            }

            # Initialize client based on authentication type
            if ':' in self.phone_or_token:
                # Bot authentication
                client = TelegramClient('bot_session', self.api_id, self.api_hash, **client_config)
                await client.start(bot_token=self.phone_or_token)
            else:
                # User authentication
                client = TelegramClient('user_session', self.api_id, self.api_hash, **client_config)
                await client.start(phone=lambda: self.phone_or_token)

            # Disable flood wait to speed up scanning
            client.flood_sleep_threshold = 0

            # Get channel and messages
            channel = await client.get_entity(self.channel_link)
            messages = await client.get_messages(channel, limit=None)
            total_messages = len(messages)

            # Process each message
            for i, message in enumerate(messages):
                if not self.is_running:
                    break

                if message.media:
                    if isinstance(message.media, (MessageMediaDocument, MessageMediaPhoto)):
                        file_info = self.get_file_info(message)
                        if file_info:
                            # Emit signal with file information
                            self.message_found.emit(file_info)
                
                # Update progress
                self.progress_updated.emit(int((i + 1) / total_messages * 100))
            
            # Clean up
            await client.disconnect()
            self.scan_finished.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))

    def run(self):
        """
        QThread run method - creates event loop and runs scan_messages
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.scan_messages())
        finally:
            loop.close()

class DownloadWorker(QThread):
    """
    Worker thread for handling file downloads from Telegram
    Implements concurrent downloads with progress tracking
    """
    # Define signals for communication with main thread
    progress_updated = pyqtSignal(int, int) # (message_id, bytes_downloaded)
    download_finished = pyqtSignal(int)   # message_id
    error_occurred = pyqtSignal(str)     # error message

    def __init__(self, api_id, api_hash, channel_link, download_folder, phone_or_token, message_ids):
        super().__init__()
         # Initialize parameters
        self.api_id = api_id
        self.api_hash = api_hash
        self.channel_link = channel_link
        self.download_folder = download_folder
        self.phone_or_token = phone_or_token
        self.message_ids = message_ids
        self.is_running = True
        self.client = None
        # Set chunk size for downloads (256KB)
        self.chunk_size = 256 * 1024
        # Limit concurrent downloads to prevent overload
        self.max_concurrent_downloads = 4

    async def download_single_file(self, message, semaphore):
        """
        Download a single file from Telegram
        Args:
            message: Telegram message containing the file
            semaphore: Asyncio semaphore for controlling concurrent downloads
        Returns:
            bool: True if download successful, False otherwise
        """
        
        async with semaphore:
            try:
                def progress_callback(downloaded_bytes, total_bytes):
                    """Callback function to track download progress"""
                    if self.is_running:
                        self.progress_updated.emit(message.id, downloaded_bytes)

                # Determine file name from message attributes
                file_name = None
                if hasattr(message.media, 'document'):
                    for attr in message.media.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            file_name = attr.file_name
                            break
                # Use default name if none found        
                if not file_name:
                    file_name = f"file_{message.id}"

                # Create full file path
                if file_name:
                    for attr in message.media.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            file_name = attr.file_name
                            break
                if not file_name:
                    file_name = f"file_{message.id}"

                file_path = os.path.join(self.download_folder, file_name)

                # Download with optimized parameters
                await self.client.download_media(
                    message,
                    file=file_path,
                    progress_callback=progress_callback
                )
                
                if self.is_running:
                    self.download_finished.emit(message.id)
                return True
            except Exception as e:
                if self.is_running:
                    self.error_occurred.emit(f"Error downloading message {message.id}: {str(e)}")
                return False

    async def download_messages(self):
        """
        Main download method handling multiple files concurrently
        """
        try:
            # Initialize client with optimized settings
            self.client = TelegramClient(
                'download_session',
                self.api_id,
                self.api_hash,
                connection=connection.ConnectionTcpFull,
                auto_reconnect=True,
                retry_delay=0,
                connection_retries=None
            )

            # Additional optimizations
            # Disable flood wait for faster downloads
            self.client.flood_sleep_threshold = 0

            # Start client
            if ':' in self.phone_or_token:
                await self.client.start(bot_token=self.phone_or_token)
            else:
                await self.client.start(phone=lambda: self.phone_or_token)

            try:
                # Try connecting to DC 2 (usually faster)
                try:
                    current_dc = await self.client.get_dc_id()
                    if current_dc != 2:
                        await self.client.connect_to_dc(2)
                except:
                    pass
                
                # Get channel and create semaphore for concurrent downloads
                channel = await self.client.get_entity(self.channel_link)
                semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
                
                # Get messages in chunks
                messages = await self.client.get_messages(channel, ids=self.message_ids)
                
                # Create download tasks
                tasks = []
                for message in messages:
                    if not self.is_running:
                        break
                    if message and hasattr(message, 'media'):
                        task = self.download_single_file(message, semaphore)
                        tasks.append(task)

                # Run downloads concurrently with optimized gathering
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

            finally:
                # Ensure client is disconnected
                if self.client:
                    await self.client.disconnect()

        except Exception as e:
            if self.is_running:
                self.error_occurred.emit(str(e))
    def run(self):
        """
        QThread run method - creates event loop and runs download_messages
        """
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the download process
            loop.run_until_complete(self.download_messages())
            
        except Exception as e:
            if self.is_running:
                self.error_occurred.emit(str(e))
        finally:
            # Clean up tasks and close loop
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # Wait for all tasks to be cancelled
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                loop.close()
            except Exception:
                pass

    def stop(self):
        """
        Stop the download process
        """
        self.is_running = False
        if self.client:
            asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.client.loop)

class TelegramDownloader(QMainWindow):
    """
    Main application window for the Telegram Channel Downloader
    Integrates all components and provides user interface
    """
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.scanner_thread = None
        self.download_worker = None
        self.download_progress_widgets = {}

    def init_ui(self):
        """
        Initialize the user interface components and layouts
        """
        # Set window properties
        self.setWindowTitle("Telegram Channel Downloader")
        self.setGeometry(200, 200, 1200, 800)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)  # Add consistent spacing


        # API credentials section
        creds_layout = QHBoxLayout()
        
        # API ID input
        self.api_id_input = QLineEdit()
        self.api_id_input.setPlaceholderText("Enter API ID")
        creds_layout.addWidget(QLabel("API ID:"))
        creds_layout.addWidget(self.api_id_input)

        # API Hash input
        self.api_hash_input = QLineEdit()
        self.api_hash_input.setPlaceholderText("Enter API Hash")
        creds_layout.addWidget(QLabel("API Hash:"))
        creds_layout.addWidget(self.api_hash_input)

        layout.addLayout(creds_layout)

        # Channel link section
        channel_layout = QHBoxLayout()
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Enter channel link or username (e.g., https://t.me/channel_name or @channel_name)")
        channel_layout.addWidget(QLabel("Channel Link:"))
        channel_layout.addWidget(self.channel_input)
        layout.addLayout(channel_layout)

        # Scan progress and button
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        layout.addWidget(self.scan_progress)

        # === Button Section ===
        button_layout = QHBoxLayout()

        # Scan button
        self.btn_scan = QPushButton("Scan Channel")
        self.btn_scan.clicked.connect(self.start_scan)
        button_layout.addWidget(self.btn_scan)

        # Select All button
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all_files)
        self.btn_select_all.setEnabled(False)
        button_layout.addWidget(self.btn_select_all)

        layout.addLayout(button_layout)

        # === File List Section ===
        self.file_list = FileListWidget()
        layout.addWidget(self.file_list)

        # Download button and progress
        self.btn_download = QPushButton("Download Selected")
        self.btn_download.clicked.connect(self.start_download)
        self.btn_download.setEnabled(False)
        layout.addWidget(self.btn_download)

        # Downloads section

        # Downloads section with proper layout
        downloads_container = QWidget()
        downloads_layout = QVBoxLayout(downloads_container)
        downloads_layout.setContentsMargins(0, 0, 0, 0)  # Remove extra margins
        # === Download Header ===
        downloads_label = QLabel("Active Downloads")
        downloads_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(downloads_label)

        # Create scroll area for downloads
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(200)  # Set minimum height
        self.scroll_area.setMaximumHeight(300)

        # Create widget to hold downloads
        self.downloads_widget = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_widget)
        self.downloads_layout.setSpacing(10)  # Add space between items
        self.downloads_layout.setAlignment(Qt.AlignTop)  # Align items to top
        
        # Add downloads widget to scroll area
        self.scroll_area.setWidget(self.downloads_widget)
        downloads_layout.addWidget(self.scroll_area)
        
        # Add downloads container to main layout
        layout.addWidget(downloads_container)
        
        
    def select_all_files(self):
        """Select all files in the file list"""
        for row in range(self.file_list.rowCount()):
            self.file_list.item(row, 0).setCheckState(Qt.Checked)

    def start_scan(self):
        """
        Start scanning the Telegram channel for files
        Validates inputs and initiates the scanner thread
        """
        # Validate inputs
        api_id = self.api_id_input.text().strip()
        api_hash = self.api_hash_input.text().strip()
        channel_link = self.channel_input.text().strip()

        if not all([api_id, api_hash, channel_link]):
            QMessageBox.warning(self, "Input Error", "Please fill in all fields")
            return

        try:
            api_id = int(api_id)
        except ValueError:
            QMessageBox.warning(self, "Input Error", "API ID must be a number")
            return

        # Get authentication details
        auth_dialog = AuthDialog(self)
        if auth_dialog.exec_() == QDialog.Accepted:
            phone_or_token = auth_dialog.phone_input.text().strip()
            if not phone_or_token:
                phone_or_token = auth_dialog.token_input.text().strip()
            
            if not phone_or_token:
                QMessageBox.warning(self, "Input Error", "Please provide either phone number or bot token")
                return
        else:
            return

        # Reset UI state
        self.file_list.setRowCount(0)
        self.file_list.files_data.clear()
        self.btn_download.setEnabled(False)
        self.btn_select_all.setEnabled(False)
        self.scan_progress.setVisible(True)
        self.scan_progress.setValue(0)
        
        # Initialize and start scanner thread
        self.scanner_thread = MessageScannerThread(api_id, api_hash, channel_link, phone_or_token)
        self.scanner_thread.progress_updated.connect(self.update_scan_progress)
        self.scanner_thread.message_found.connect(self.add_file_to_list)
        self.scanner_thread.scan_finished.connect(self.scan_completed)
        self.scanner_thread.error_occurred.connect(self.handle_error)
        
        self.scanner_thread.start()
        self.btn_scan.setEnabled(False)

    def update_scan_progress(self, progress):
        """Update the scan progress bar"""
        self.scan_progress.setValue(progress)

    def add_file_to_list(self, file_info):
        """Add a found file to the file list"""

        file_name = file_info['name']
        if file_info['type'] == "Video" and 'duration' in file_info and file_info['duration']:
        # Add duration to the name for videos
            duration = str(datetime.timedelta(seconds=file_info['duration']))
            file_name = f"{file_name} ({duration})"

        self.file_list.add_file(
            file_info['message_id'],
            file_info['type'],
            file_info['name'],
            file_info['size'],
            file_info['date'],
            file_info['format']
        )
        self.btn_download.setEnabled(True)
        self.btn_select_all.setEnabled(True)

    def scan_completed(self):
        """Handle scan completion"""
        self.btn_scan.setEnabled(True)
        self.scan_progress.setVisible(False)
        QMessageBox.information(self, "Scan Complete", "Channel scan completed successfully!")

    def handle_error(self, error_message):
        """Handle errors from scanner or downloader"""
        self.btn_scan.setEnabled(True)
        self.scan_progress.setVisible(False)
        QMessageBox.critical(self, "Error", f"An error occurred: {error_message}")

    def start_download(self):
        """
        Start downloading selected files
        Initiates the download worker thread
        """
        # Get selected files
        selected_files = self.file_list.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, "Selection Error", "Please select files to download")
            return

        # Get download directory
        download_dir = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if not download_dir:
            return

        # Get credentials
        api_id = int(self.api_id_input.text().strip())
        api_hash = self.api_hash_input.text().strip()
        channel_link = self.channel_input.text().strip()
        
        # Get authentication
        auth_dialog = AuthDialog(self)
        if auth_dialog.exec_() == QDialog.Accepted:
            phone_or_token = auth_dialog.phone_input.text().strip()
            if not phone_or_token:
                phone_or_token = auth_dialog.token_input.text().strip()
            
            if not phone_or_token:
                QMessageBox.warning(self, "Input Error", "Please provide either phone number or bot token")
                return
        else:
            return
            
        # Create progress widgets for selected files
        for file_info in selected_files:
            if file_info['message_id'] not in self.download_progress_widgets:
                progress_widget = DownloadProgressWidget(file_info)
                self.download_progress_widgets[file_info['message_id']] = progress_widget
                self.downloads_layout.addWidget(progress_widget)
        
        # Start download worker
        message_ids = [file['message_id'] for file in selected_files]
        self.download_worker = DownloadWorker(
            api_id, api_hash, channel_link, download_dir, phone_or_token, message_ids
        )
        self.download_worker.progress_updated.connect(self.update_download_progress)
        self.download_worker.download_finished.connect(self.file_download_completed)
        self.download_worker.error_occurred.connect(self.handle_error)
        
        self.download_worker.start()
        self.btn_download.setEnabled(False)

    def update_download_progress(self, message_id, bytes_downloaded):
        """Update progress for a specific file download"""
        if message_id in self.download_progress_widgets:
            self.download_progress_widgets[message_id].update_progress(bytes_downloaded)

    def file_download_completed(self, message_id):
        """Handle completion of individual file download"""
        if message_id in self.download_progress_widgets:
            widget = self.download_progress_widgets.pop(message_id)
            self.downloads_layout.removeWidget(widget)
            widget.deleteLater()

        if not self.download_progress_widgets:
            self.btn_download.setEnabled(True)
            QMessageBox.information(self, "Download Complete", "All files have been downloaded successfully!")

    def closeEvent(self, event):
        """Handle application closure"""
        # Properly clean up when closing the application
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.stop()
            self.download_worker.wait()
        event.accept()
        
def main():
    """
    Application entry point
    Creates and runs the main application window
    """
    app = QApplication(sys.argv)
    window = TelegramDownloader()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()