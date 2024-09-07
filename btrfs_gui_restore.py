import sys
import os
import stat
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTextEdit, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QComboBox, QCheckBox)
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QScrollArea
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPalette, QColor
import sys
import subprocess
import re

class BtrfsListWorker(QThread):
    finished = pyqtSignal(list, dict)
    progress = pyqtSignal(str)

    def __init__(self, device, use_sudo, path_regex, destination='/tmp/btrfs_recovery'):
        super().__init__()
        self.device = device
        self.use_sudo = use_sudo
        self.path_regex = path_regex
        self.destination = destination

    def run(self):
        try:
            self.list_deleted_files()
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            self.finished.emit([], {})

    def list_deleted_files(self):
        roots = self.find_roots()
        
        if not roots:
            self.progress.emit("Error: Could not find any valid roots.")
            self.finished.emit([], {})
            return

        deleted_files = set()
        successful_roots = {}
        for root in roots:
            command = ['btrfs', 'restore', '-t', root, '-Divv', '--path-regex', self.path_regex, self.device, '/dev/null']
            if self.use_sudo:
                command = ['sudo'] + command
            
            self.progress.emit(f"Executing command: {' '.join(command)}")
            files = self.execute_command(command)
            if files:
                deleted_files.update(files)
                successful_roots[root] = files

        self.finished.emit(list(deleted_files), successful_roots)
    def find_roots(self):
        find_root_command = ['btrfs-find-root', self.device]
        if self.use_sudo:
            find_root_command = ['sudo'] + find_root_command
        
        self.progress.emit(f"Finding roots: {' '.join(find_root_command)}")
        process = subprocess.Popen(find_root_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        roots = []
        for line in process.stdout:
            if "Well block" in line:
                root = re.search(r'Well block (\d+)', line)
                if root:
                    roots.append(root.group(1))
        return roots

    def execute_command(self, command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        deleted_files = set()
        for line in process.stdout:
            self.progress.emit(line.strip())
            if line.startswith("Restoring"):
                parts = line.split()
                if len(parts) >= 2:
                    path = parts[1].replace('/dev/null/', '')
                    deleted_files.add(path)
        
        process.wait()
        return deleted_files


class ColorScheme:
    def __init__(self, dark_mode=False):
        self.dark_mode = dark_mode
        self.update_colors()

    def update_colors(self):
        if self.dark_mode:
            self.background = QColor(18, 18, 18)
            self.text = QColor(255, 255, 255)
            self.accent = QColor(0, 176, 255)  # A vibrant blue
            self.secondary_background = QColor(30, 30, 30)
            self.border = QColor(60, 60, 60)
        else:
            self.background = QColor(245, 245, 245)
            self.text = QColor(0, 0, 0)
            self.accent = QColor(0, 120, 212)  # A softer blue for light mode
            self.secondary_background = QColor(255, 255, 255)
            self.border = QColor(200, 200, 200)

    def apply_to_app(self, app):
        palette = QPalette()
        palette.setColor(QPalette.Window, self.background)
        palette.setColor(QPalette.WindowText, self.text)
        palette.setColor(QPalette.Base, self.secondary_background)
        palette.setColor(QPalette.AlternateBase, self.background)
        palette.setColor(QPalette.ToolTipBase, self.background)
        palette.setColor(QPalette.ToolTipText, self.text)
        palette.setColor(QPalette.Text, self.text)
        palette.setColor(QPalette.Button, self.background)
        palette.setColor(QPalette.ButtonText, self.text)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, self.accent)
        palette.setColor(QPalette.Highlight, self.accent)
        palette.setColor(QPalette.HighlightedText, self.background)
        app.setPalette(palette)

        # Set stylesheet for more detailed control
        app.setStyleSheet(f"""
            QMainWindow, QDialog {{ background-color: {self.background.name()}; }}
            QPushButton {{ 
                background-color: {self.accent.name()}; 
                color: {self.background.name()}; 
                border: none; 
                padding: 8px 15px; 
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {self.accent.lighter(110).name()}; 
            }}
            QPushButton:pressed {{ 
                background-color: {self.accent.darker(110).name()}; 
            }}
            QLineEdit, QTextEdit, QComboBox {{ 
                background-color: {self.secondary_background.name()}; 
                border: 1px solid {self.border.name()}; 
                padding: 5px; 
                border-radius: 4px;
                color: {self.text.name()};
            }}
            QTableWidget {{ 
                background-color: {self.secondary_background.name()}; 
                border: 1px solid {self.border.name()}; 
                gridline-color: {self.border.name()};
            }}
            QHeaderView::section {{ 
                background-color: {self.background.name()}; 
                color: {self.text.name()}; 
                padding: 5px;
                border: 1px solid {self.border.name()};
            }}
            QLabel {{ color: {self.text.name()}; }}
            QTextBrowser {{ 
                background-color: {self.secondary_background.name()}; 
                color: {self.text.name()};
                border: 1px solid {self.border.name()};
                padding: 5px;
                border-radius: 4px;
            }}
        """)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CatNode BTRFS Recovery Tool by - Ksauraj")
        self.setGeometry(100, 100, 800, 600)
        self.color_scheme = ColorScheme(dark_mode=True)  # Default to dark mode
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        self.faq_button = QPushButton("FAQ")
        self.faq_button.clicked.connect(self.show_faq)
        layout.addWidget(self.faq_button)
        self.successful_roots = {}

        # BTRFS partition selection
        partition_layout = QHBoxLayout()
        self.partition_combo = QComboBox()
        self.partition_combo.currentIndexChanged.connect(self.on_partition_selected)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_partitions)
        unmount_button = QPushButton("Unmount")
        unmount_button.clicked.connect(self.unmount_selected)
        partition_layout.addWidget(QLabel("BTRFS Partitions:"))
        partition_layout.addWidget(self.partition_combo)
        partition_layout.addWidget(refresh_button)
        partition_layout.addWidget(unmount_button)
        layout.addLayout(partition_layout)

        # Add depth selection
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Search Depth:"))
        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["Basic", "Advanced", "Deep"])
        depth_layout.addWidget(self.depth_combo)
        layout.addLayout(depth_layout)

        # Add regex type selection
        regex_type_layout = QHBoxLayout()
        regex_type_layout.addWidget(QLabel("Recovery Type:"))
        self.regex_type = QComboBox()
        self.regex_type.addItems(["Specific File", "Specific Directory", "File Extension", "File in Directory", "Everything"])
        self.regex_type.currentIndexChanged.connect(self.update_regex_hint)
        regex_type_layout.addWidget(self.regex_type)
        layout.addLayout(regex_type_layout)

        # Add regex input
        regex_input_layout = QHBoxLayout()
        regex_input_layout.addWidget(QLabel("Path/Filename:"))
        self.regex_input = QLineEdit()
        self.regex_input.setPlaceholderText("Enter path or filename")
        regex_input_layout.addWidget(self.regex_input)
        layout.addLayout(regex_input_layout)

        # Device input
        device_layout = QHBoxLayout()
        device_label = QLabel("Device:")
        self.device_input = QLineEdit()
        device_button = QPushButton("Browse")
        device_button.clicked.connect(self.browse_device)
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_input)
        device_layout.addWidget(device_button)
        layout.addLayout(device_layout)

        # Destination input
        dest_layout = QHBoxLayout()
        dest_label = QLabel("Destination:")
        self.dest_input = QLineEdit()
        dest_button = QPushButton("Browse")
        dest_button.clicked.connect(self.browse_destination)
        dest_layout.addWidget(dest_label)
        dest_layout.addWidget(self.dest_input)
        dest_layout.addWidget(dest_button)
        layout.addLayout(dest_layout)

        # Sudo checkbox
        self.sudo_checkbox = QCheckBox("Use sudo")
        layout.addWidget(self.sudo_checkbox)

        # List and Restore buttons
        button_layout = QHBoxLayout()
        self.list_button = QPushButton("List Deleted Files")
        self.list_button.clicked.connect(self.list_deleted_files)
        self.restore_button = QPushButton("Restore Selected Files")
        self.restore_button.clicked.connect(self.start_restore)
        self.restore_button.setEnabled(False)
        button_layout.addWidget(self.list_button)
        button_layout.addWidget(self.restore_button)
        layout.addLayout(button_layout)

        # Sorting options
        sort_layout = QHBoxLayout()
        sort_label = QLabel("Sort by:")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Size", "Date"])
        self.sort_combo.currentIndexChanged.connect(self.sort_files)
        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(self.sort_combo)
        layout.addLayout(sort_layout)

        # File list table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["File Name", "Size", "Date"])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.MultiSelection)
        layout.addWidget(self.file_table)

        # Output area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)

        self.deleted_files = []
        self.refresh_partitions()
        self.mode_toggle = QPushButton("Switch to Light Mode")
        self.mode_toggle.clicked.connect(self.toggle_mode)
        layout.addWidget(self.mode_toggle)

        self.deleted_files = []
        self.refresh_partitions()

    def toggle_mode(self):
        self.color_scheme.dark_mode = not self.color_scheme.dark_mode
        self.color_scheme.update_colors()
        self.color_scheme.apply_to_app(QApplication.instance())
        self.mode_toggle.setText("Switch to Light Mode" if self.color_scheme.dark_mode else "Switch to Dark Mode")

    def update_regex_hint(self, index):
        hints = [
            "Enter filename (e.g., important.txt)",
            "Enter directory name (e.g., documents)",
            "Enter file extension (e.g., jpg)",
            "Enter directory/filename (e.g., work/report.pdf)",
            "Leave blank to recover everything"
        ]
        self.regex_input.setPlaceholderText(hints[index])

    def browse_device(self):
        device_path, _ = QFileDialog.getOpenFileName(self, "Select BTRFS Device", 
                                                     filter="Block Devices (*);;All Files (*)")
        if device_path:
            self.device_input.setText(device_path)

    def browse_destination(self):
        destination = QFileDialog.getExistingDirectory(self, "Select Destination")
        if destination:
            self.dest_input.setText(destination)

    def list_btrfs_partitions(self):
        try:
            result = subprocess.run(['sudo', 'btrfs', 'filesystem', 'show'], capture_output=True, text=True)
            
            partitions = []
            current_uuid = None
            current_label = None
            for line in result.stdout.split('\n'):
                if line.startswith('Label:'):
                    parts = line.split()
                    current_label = parts[1].strip("'")
                    current_uuid = parts[-1]
                elif line.strip().startswith('devid'):
                    parts = line.split()
                    device = parts[-1]
                    if current_uuid and device:
                        partition_info = f"{device} (UUID: {current_uuid}, Label: {current_label})"
                        partitions.append(partition_info)
                    current_uuid = None
                    current_label = None
            
            return partitions
        except Exception as e:
            self.output_area.append(f"Error listing BTRFS partitions: {str(e)}")
            return []

    def refresh_partitions(self):
        partitions = self.list_btrfs_partitions()
        self.partition_combo.clear()
        if partitions:
            self.partition_combo.addItems(partitions)
            self.output_area.append("Partitions refreshed successfully.")
            # Set the device input to the first partition
            first_partition = partitions[0].split()[0]
            self.device_input.setText(first_partition)
        else:
            self.output_area.append("No BTRFS partitions found or an error occurred.")

    def on_partition_selected(self, index):
        selected = self.partition_combo.currentText()
        if selected:
            device = selected.split()[0]
            self.device_input.setText(device)
            self.output_area.append(f"Selected partition: {selected}")
        else:
            self.output_area.append("No partition selected")

    def unmount_partition(self, device):
        try:
            subprocess.run(['sudo', 'umount', device], check=True)
            self.output_area.append(f"Successfully unmounted {device}")
        except subprocess.CalledProcessError:
            self.output_area.append(f"Failed to unmount {device}. It might not be mounted.")
        except Exception as e:
            self.output_area.append(f"Error unmounting {device}: {str(e)}")

    def unmount_selected(self):
        selected = self.partition_combo.currentText()
        if selected:
            device = selected.split()[0]
            self.unmount_partition(device)
            self.refresh_partitions()
        else:
            self.output_area.append("No partition selected")

    def list_deleted_files(self):
        device = self.device_input.text()
        destination = self.dest_input.text() or '/tmp/btrfs_recovery'
        if not device:
            self.output_area.append("Please select a BTRFS device or partition.")
            return
        
        if not os.path.exists(device):
            self.output_area.append(f"Error: Device '{device}' does not exist.")
            return
        
        if not os.path.isfile(device) and not stat.S_ISBLK(os.stat(device).st_mode):
            self.output_area.append(f"Error: '{device}' is not a block device or regular file.")
            return

        # Try to unmount the partition
        try:
            subprocess.run(['sudo', 'umount', device], check=True)
            self.output_area.append(f"Successfully unmounted {device}")
        except subprocess.CalledProcessError:
            self.output_area.append(f"Note: {device} was not mounted or couldn't be unmounted.")

        self.list_button.setEnabled(False)
        self.output_area.clear()
        self.output_area.append("Starting file recovery...")

        regex_type = self.regex_type.currentIndex()
        user_input = self.regex_input.text()

        if regex_type == 0:  # Specific File
            path_regex = f"/{user_input}"
        elif regex_type == 1:  # Specific Directory
            path_regex = f"/{user_input}/."
        elif regex_type == 2:  # File Extension
            path_regex = f"/.*\\.{user_input}"
        elif regex_type == 3:  # File in Directory
            path_regex = f"/{user_input}"
        else:  # Everything
            path_regex = "/."

        self.output_area.append(f"Using path regex: {path_regex}")

        self.worker = BtrfsListWorker(device, self.sudo_checkbox.isChecked(), path_regex, destination)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.update_file_list)
        self.worker.start()

    def update_progress(self, message):
        self.output_area.append(message)

    def update_file_list(self, files, successful_roots):
        self.deleted_files = files
        self.successful_roots = successful_roots
        self.populate_table()
        self.list_button.setEnabled(True)
        self.restore_button.setEnabled(True)

    def populate_table(self):
        self.file_table.setRowCount(len(self.deleted_files))
        for row, path in enumerate(self.deleted_files):
            self.file_table.setItem(row, 0, QTableWidgetItem(path))
            # Get file size and modification date if the file exists
            if os.path.exists(path):
                size = os.path.getsize(path)
                date = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                size = "Unknown"
                date = "Unknown"
            self.file_table.setItem(row, 1, QTableWidgetItem(str(size)))
            self.file_table.setItem(row, 2, QTableWidgetItem(date))

    def sort_files(self, index):
        if index == 0:  # Name
            self.deleted_files.sort()
        elif index == 1:  # Size
            self.deleted_files.sort(key=lambda x: os.path.getsize(x) if os.path.exists(x) else 0, reverse=True)
        elif index == 2:  # Date
            self.deleted_files.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)
        self.populate_table()

    def start_restore(self):
        device = self.device_input.text()
        destination = self.dest_input.text() or '/tmp/btrfs_recovery'
        selected_rows = set(index.row() for index in self.file_table.selectedIndexes())
        selected_files = [self.deleted_files[row] for row in selected_rows]

        if not (device and destination and selected_files):
            self.output_area.append("Please fill in all fields and select files to restore.")
            return

        self.restore_button.setEnabled(False)
        self.output_area.clear()
        self.output_area.append("Starting restoration process...")

        # Ensure the destination directory exists
        os.makedirs(destination, exist_ok=True)

        for file in selected_files:
            # Find the correct root for this file
            root = self.find_root_for_file(file)
            if not root:
                self.output_area.append(f"Error: Could not find a valid root for {file}")
                continue

            command = ['sudo', 'btrfs', 'restore', '-ivv', '-t', root, '--path-regex', f'/{re.escape(file)}$', device, destination]
            
            self.output_area.append(f"Executing command: {' '.join(command)}")
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in process.stdout:
                self.output_area.append(line.strip())
            
            process.wait()

        self.restore_button.setEnabled(True)
        self.output_area.append("Restoration process completed.")

    def find_root_for_file(self, file):
        for root, files in self.successful_roots.items():
            if file in files:
                return root
        return None
    
    def show_faq(self):
        faq_dialog = FAQDialog(self)
        faq_dialog.exec_()


class FAQDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CatNode BTRFS Recovery Tool - FAQs")
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        scroll = QScrollArea()
        content = QTextBrowser()
        content.setOpenExternalLinks(True)
        content.setHtml(self.get_faq_content())
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)

        layout.addWidget(scroll)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def get_faq_content(self):
        # This method will return the HTML content of the FAQs
        return """
        <h1>CatNode BTRFS Recovery Tool - FAQs and Related Information</h1>

        <h2>General Questions</h2>

        <h3>Q1: What is the CatNode BTRFS Recovery Tool?</h3>
        <p>A: The CatNode BTRFS Recovery Tool is a graphical user interface application designed to facilitate the recovery of deleted files from BTRFS filesystems. It provides an easy-to-use interface for listing and restoring deleted files on BTRFS partitions.</p>

        <h3>Q2: Who developed this tool?</h3>
        <p>A: This tool was developed by Ksauraj.</p>

        <h3>Q3: Is this tool free to use?</h3>
        <p>A: Check License page for more information.</p>

        <h2>Technical Questions</h2>

        <h3>Q4: What are the system requirements for running this tool?</h3>
        <p>A: The tool requires:
        <ul>
            <li>Python 3.6 or higher</li>
            <li>PyQt5</li>
            <li>BTRFS utilities (btrfs-progs)</li>
            <li>A system with BTRFS filesystem support</li>
        </ul></p>

        <h3>Q5: On which operating systems can I run this tool?</h3>
        <p>A: The tool is primarily designed for Linux systems with BTRFS support. It may work on macOS and Windows (via WSL) with limitations.</p>

        <h3>Q6: How does the tool recover deleted files?</h3>
        <p>A: The tool uses the BTRFS filesystem's ability to access previous states of the filesystem. It searches for and restores deleted files using the `btrfs restore` command with specific parameters.</p>

        <h2>Usage Questions</h2>

        <h3>Q7: How do I start the recovery process?</h3>
        <p>A:
        <ol>
            <li>Run the application</li>
            <li>Select the BTRFS partition</li>
            <li>Choose search criteria (file type, directory, etc.)</li>
            <li>Click "List Deleted Files"</li>
            <li>Select files to recover</li>
            <li>Specify a destination</li>
            <li>Click "Restore Selected Files"</li>
        </ol></p>

        <h3>Q8: Why can't I see my BTRFS partition in the tool?</h3>
        <p>A: Ensure that:
        <ul>
            <li>The partition is properly mounted</li>
            <li>You have the necessary permissions to access the partition</li>
            <li>The partition is indeed a BTRFS filesystem</li>
        </ul></p>

        <h3>Q9: The tool isn't recovering my files. What could be wrong?</h3>
        <p>A: Several factors can affect file recovery:
        <ul>
            <li>Time elapsed since deletion</li>
            <li>Filesystem activity after deletion</li>
            <li>File fragmentation</li>
            <li>Filesystem errors or corruption</li>
        </ul></p>

        <h3>Q10: Is it guaranteed that I'll recover all my deleted files?</h3>
        <p>A: No, file recovery is not guaranteed. Success depends on various factors including how long ago the file was deleted and subsequent filesystem activity.</p>

        <h2>BTRFS-Specific Questions</h2>

        <h3>Q11: What is BTRFS?</h3>
        <p>A: BTRFS (B-Tree File System) is a modern copy-on-write (CoW) filesystem for Linux aimed at implementing advanced features while focusing on fault tolerance, repair, and easy administration.</p>

        <h3>Q12: How does BTRFS handle deleted files differently from other filesystems?</h3>
        <p>A: BTRFS uses a copy-on-write mechanism, which can preserve older versions of files and metadata. This feature is what allows for the potential recovery of deleted files.</p>

        <h3>Q13: What are BTRFS snapshots and how do they relate to file recovery?</h3>
        <p>A: BTRFS snapshots are point-in-time copies of the filesystem. They can be very useful for recovering deleted files if a snapshot was taken before the deletion occurred.</p>

        <h2>Troubleshooting</h2>

        <h3>Q14: I'm getting a "parent transid verify failed" error. What does this mean?</h3>
        <p>A: This error suggests that the filesystem's state has changed since the file was deleted. It may still be possible to recover the file, but with a higher risk of corruption or incomplete data.</p>

        <h3>Q15: The tool says "Invalid mapping for [block range]". Can I still recover my file?</h3>
        <p>A: This error indicates that the filesystem's metadata for the file has been altered. Recovery might be partial or impossible in this case.</p>

        <h3>Q16: How can I increase my chances of successful file recovery?</h3>
        <p>A:
        <ul>
            <li>Act quickly after realizing a file has been deleted</li>
            <li>Minimize write operations to the filesystem after deletion</li>
            <li>Regularly create and maintain BTRFS snapshots</li>
            <li>Consider using BTRFS with multiple devices for redundancy</li>
        </ul></p>

        <h2>Best Practices</h2>

        <h3>Q17: How can I prevent data loss in the future?</h3>
        <p>A:
        <ul>
            <li>Regularly backup your important data</li>
            <li>Use BTRFS features like snapshots</li>
            <li>Be cautious when deleting files</li>
            <li>Keep your filesystem healthy with regular maintenance</li>
        </ul></p>

        <h3>Q18: Are there any risks in using this recovery tool?</h3>
        <p>A: While the tool is designed to be non-destructive, there's always a small risk when performing filesystem operations. It's recommended to work on a copy of the filesystem when possible.</p>

        <p><em>Remember, while this tool aims to assist in file recovery, it's always best to maintain regular backups of important data to prevent loss.</em></p>
        """

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.color_scheme.apply_to_app(app)
    window.show()   
    sys.exit(app.exec_())