"""
File System Monitor

This script monitors all files in a specified directory and its subdirectories.
It prints messages to the console when files are created, deleted, modified, or moved.
"""

import time
import sys
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Optional


class FileEventHandler(FileSystemEventHandler):
    """Handles file system events for monitoring."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def on_created(self, event):
        if not event.is_directory:
            print(f"Created: {event.src_path}")

    def on_deleted(self, event):
        if not event.is_directory:
            print(f"Deleted: {event.src_path}")

    def on_modified(self, event):
        if not event.is_directory:
            print(f"Modified: {event.src_path}")

    def on_moved(self, event):
        if not event.is_directory:
            print(f"Moved/Renamed: From '{event.src_path}' to '{event.dest_path}'")


def validate_directory(path: str) -> bool:
    """Validate that the directory exists and is accessible."""
    if not os.path.exists(path):
        print(f"Error: The specified path '{path}' does not exist.")
        return False
    
    if not os.path.isdir(path):
        print(f"Error: The specified path '{path}' is not a directory.")
        return False
    
    if not os.access(path, os.R_OK):
        print(f"Error: No read permission for directory '{path}'.")
        return False
    
    return True


def get_default_directory() -> str:
    """Get the default directory to monitor based on the current working directory."""
    return str(Path.cwd())


def start_monitoring(directory_path: str, recursive: bool = True) -> None:
    """Start monitoring the specified directory."""
    event_handler = FileEventHandler()
    observer = Observer()
    observer.schedule(event_handler, directory_path, recursive=recursive)

    print(f"Monitoring directory: {directory_path}")
    print("Press Ctrl+C to stop monitoring.")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nMonitoring stopped.")
    finally:
        observer.join()


def main() -> None:
    """Main function to handle command line arguments and start monitoring."""
    # Parse command line arguments
    if len(sys.argv) > 1:
        directory_to_monitor = sys.argv[1]
    else:
        directory_to_monitor = get_default_directory()
        print(f"No directory specified. Monitoring current directory: {directory_to_monitor}")
        print("To monitor a specific directory, run: python monitor-all-files.py /path/to/directory")

    # Validate directory
    if not validate_directory(directory_to_monitor):
        sys.exit(1)

    # Start monitoring
    start_monitoring(directory_to_monitor)


if __name__ == "__main__":
    main()
