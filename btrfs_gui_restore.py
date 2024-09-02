import sys
import os
import stat
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTextEdit, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QComboBox, QCheckBox)
import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import subprocess
import re

class BtrfsListWorker(QThread):
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def __init__(self, device, use_sudo, path_regex, depth=0):
        super().__init__()
        self.device = device
        self.use_sudo = use_sudo
        self.path_regex = path_regex
        self.depth = depth

    def run(self):
        try:
            if self.depth == 0:
                self.basic_restore()
            elif self.depth in [1, 2]:
                self.advanced_restore()
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            self.finished.emit([])

    def basic_restore(self):
        command = ['btrfs', 'restore', '-Divv', '--path-regex', self.path_regex, self.device, '/dev/null']
        if self.use_sudo:
            command = ['sudo'] + command
        
        self.progress.emit(f"Executing command: {' '.join(command)}")
        self.execute_command(command)

    def advanced_restore(self):
        roots = self.find_roots()
        for root in roots:
            command = ['btrfs', 'restore', '-t', root, '-Divv', '--path-regex', self.path_regex, self.device, '/dev/null']
            if self.use_sudo:
                command = ['sudo'] + command
            
            self.progress.emit(f"Executing command: {' '.join(command)}")
            self.execute_command(command)

    def find_roots(self):
        command = ['btrfs-find-root', self.device]
        if self.depth == 2:
            command.insert(1, '-a')
        if self.use_sudo:
            command = ['sudo'] + command
        
        self.progress.emit(f"Finding roots: {' '.join(command)}")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        roots = []
        for line in process.stdout:
            if "Well block" in line:
                root = re.search(r'Well block (\d+)', line)
                if root:
                    roots.append(root.group(1))
        return roots

    def execute_command(self, command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        deleted_files = []
        for line in process.stdout:
            self.progress.emit(line.strip())
            if line.startswith("Restoring"):
                parts = line.split()
                if len(parts) >= 3:
                    path = parts[1]
                    size = parts[2].strip('()')
                    deleted_files.append((path, size, "Unknown"))
        
        process.wait()
        self.finished.emit(deleted_files)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BTRFS Restore GUI")
        self.setGeometry(100, 100, 800, 600)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

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

        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["Basic", "Advanced", "Deep"])
        layout.addWidget(QLabel("Search Depth:"))
        layout.addWidget(self.depth_combo)

        # Add regex input
        self.regex_input = QLineEdit()
        layout.addWidget(QLabel("Path Regex:"))
        layout.addWidget(self.regex_input)

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

        self.deleted_files = []
        self.refresh_partitions()

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
            
            print("Raw output:")
            print(result.stdout)
            print("Error output:")
            print(result.stderr)
            
            partitions = []
            current_uuid = None
            current_label = None
            for line in result.stdout.split('\n'):
                print(f"Processing line: {line}")  # Debug print
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
                        print(f"Added partition: {partition_info}")  # Debug print
                    current_uuid = None
                    current_label = None
            
            print(f"Final partitions list: {partitions}")  # Debug print
            return partitions
        except Exception as e:
            self.output_area.append(f"Error listing BTRFS partitions: {str(e)}")
            print(f"Exception in list_btrfs_partitions: {str(e)}")  # Debug print
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
        print(f"Partitions added to combo box: {partitions}")  # Debug print

    def on_partition_selected(self, index):
        selected = self.partition_combo.currentText()
        if selected:
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
        self.output_area.append("Listing deleted files...")

        depth = self.depth_combo.currentIndex()
        
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

        self.worker = BtrfsListWorker(device, self.sudo_checkbox.isChecked(), path_regex, depth)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.update_file_list)
        self.worker.start()

    def update_file_list(self, files):
        self.deleted_files = files
        self.populate_table()
        self.list_button.setEnabled(True)
        self.restore_button.setEnabled(True)

    def populate_table(self):
        self.file_table.setRowCount(len(self.deleted_files))
        for row, (path, size, date) in enumerate(self.deleted_files):
            self.file_table.setItem(row, 0, QTableWidgetItem(path))
            self.file_table.setItem(row, 1, QTableWidgetItem(size))
            self.file_table.setItem(row, 2, QTableWidgetItem(date))

    def sort_files(self, index):
        if index == 0:  # Name
            self.deleted_files.sort(key=lambda x: x[0])
        elif index == 1:  # Size
            self.deleted_files.sort(key=lambda x: int(x[1].split()[0]), reverse=True)
        elif index == 2:  # Date
            self.deleted_files.sort(key=lambda x: x[2], reverse=True)
        self.populate_table()        

    def start_restore(self):
        device = self.partition_combo.currentText() or self.device_input.text()
        destination = self.dest_input.text()
        selected_rows = set(index.row() for index in self.file_table.selectedIndexes())
        selected_files = [self.deleted_files[row][0] for row in selected_rows]

        if not (device and destination and selected_files):
            self.output_area.append("Please fill in all fields and select files to restore.")
            return

        self.restore_button.setEnabled(False)
        self.output_area.clear()
        self.output_area.append("Starting restoration process...")

        # Implement the restoration process here
        # You may want to create a new worker thread for this operation

    def update_progress(self, message):
        self.output_area.append(message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())