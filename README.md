# CatNode BTRFS Recovery Tool

## Overview

CatNode BTRFS Recovery Tool is a graphical user interface application designed to facilitate the recovery of deleted files from BTRFS filesystems. Developed by Ksauraj, this tool provides an easy-to-use interface for listing and restoring deleted files on BTRFS partitions.

## Features

- List BTRFS partitions on the system
- Unmount selected partitions
- Search for deleted files using various criteria:
  - Specific file
  - Specific directory
  - File extension
  - File in directory
  - Everything (all deleted files)
- Display list of recoverable files
- Restore selected files to a specified destination
- Support for using sudo for elevated privileges

## Requirements

- Python 3.6+
- PyQt5
- BTRFS utilities (btrfs-progs)

## Installing BTRFS Utilities (btrfs-progs)

The CatNode BTRFS Recovery Tool requires btrfs-progs to be installed on your system. Follow the instructions for your operating system:

### Linux

#### Debian/Ubuntu and derivatives:
```
sudo apt update
sudo apt install btrfs-progs
```

#### Fedora:
```
sudo dnf install btrfs-progs
```

#### Arch Linux and derivatives:
```
sudo pacman -S btrfs-progs
```

#### openSUSE:
```
sudo zypper install btrfs-progs
```

### macOS

BTRFS is not natively supported on macOS, but you can install btrfs-progs using Homebrew:

1. Install Homebrew if you haven't already:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install btrfs-progs:
   ```
   brew install btrfs-progs
   ```

Note: BTRFS functionality may be limited on macOS.

### Windows

BTRFS is not natively supported on Windows. However, you can use Windows Subsystem for Linux (WSL) to run the tool:

1. Install WSL by following Microsoft's official guide: https://docs.microsoft.com/en-us/windows/wsl/install

2. Install a Linux distribution from the Microsoft Store (e.g., Ubuntu)

3. Open your WSL terminal and follow the Linux instructions above to install btrfs-progs

### FreeBSD

On FreeBSD, you can install btrfs-progs from ports:

```
cd /usr/ports/sysutils/btrfs-progs
make install clean
```

Or using pkg:

```
pkg install sysutils/btrfs-progs
```

### OpenBSD

BTRFS is not officially supported on OpenBSD. You may need to compile btrfs-progs from source or use an alternative method to access BTRFS filesystems.

---

After installing btrfs-progs, you should be able to run the CatNode BTRFS Recovery Tool on your system. Please note that BTRFS support and functionality may vary depending on your operating system and version of btrfs-progs.

## Installation

1. Ensure you have Python 3.6 or higher installed on your system.
2. Install the required Python packages:

   ```
   pip install PyQt5
   ```

3. Clone this repository or download the source code.

## Usage

1. Run the application:

   ```
   python btrfs_restore_gui.py
   ```

2. Select the BTRFS partition you want to recover files from.
3. Choose the search criteria and enter any necessary details (e.g., file extension).
4. Click "List Deleted Files" to see recoverable files.
5. Select the files you want to restore from the list.
6. Specify a destination directory for the recovered files.
7. Click "Restore Selected Files" to begin the recovery process.

## Note

This tool is in continuous development. While efforts have been made to ensure its reliability, please use it with caution, especially on critical systems. Always back up important data before attempting file recovery.

## Contributing

Contributions to the CatNode BTRFS Recovery Tool are welcome. Please feel free to submit pull requests or create issues for bugs and feature requests.

## Disclaimer

This tool is provided as-is, without any warranties. The author and contributors are not responsible for any data loss or system damage that may occur from using this tool. Use at your own risk.
