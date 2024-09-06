import os
import shutil
import sys
import threading
import time
import hashlib
from datetime import datetime
from threading import Event
from typing import Union, Optional


class FolderNotFoundError(Exception):
    """Exception raised when a folder is not found."""
    pass


def calculate_sha1(file_path: str) -> str:
    """Calculate SHA-1 hash of a file."""
    hash_sha1 = hashlib.sha1()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash_sha1.update(chunk)
    return hash_sha1.hexdigest()


def get_log_file_path(log_dir: str) -> str:
    """Get the path for the log file."""
    return os.path.join(log_dir, "sync_logs.log")


def log_message(log_file_path: str, message: str) -> None:
    """Log a message to the log file and print it to the console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    with open(log_file_path, "a") as file:
        if message == "***":
            file.write(message + "\n")
        else:
            file.write(log_entry + "\n")
    print(log_entry)


def check_input(source_dir: str, replica_dir: str, interval: str) -> None:
    """Check the validity of input directories and interval."""
    if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
        raise FolderNotFoundError(f"Source dir '{source_dir}' does not exist!")

    if not os.path.exists(replica_dir) or not os.path.isdir(replica_dir):
        raise FolderNotFoundError(f"Replica dir '{replica_dir}' does not exist!")

    try:
        int(interval)
    except ValueError:
        print("Interval must be an integer.")
        sys.exit(1)


def get_file_size(file_path: str) -> int:
    """Return the size of a file in bytes."""
    return os.path.getsize(file_path)


def get_file_modification_date(file_path: str) -> str:
    """Return the last modification date of a file."""
    mod_timestamp = os.path.getmtime(file_path)
    mod_date = datetime.fromtimestamp(mod_timestamp)
    return mod_date.strftime("%Y-%m-%d %H:%M:%S")


def log_error(log_file_path: str, error_type: Union[str, Exception],
              source_file: Optional[str], replica_file: Optional[str], operation: str) -> None:
    """Log an error message."""
    if error_type == "PermissionError":
        log_message(log_file_path, f"Permission denied: Could not {operation} "
                                   f"file '{source_file}' to '{replica_file}'")
    else:
        log_message(log_file_path, f"OS error while {operation} file '{source_file}' "
                                   f"to '{replica_file}': {str(error_type)}")


def copy_or_update_file(source_file: str, replica_file: str, clean_log_path: str,
                        log_file_path: str, changes: list, is_update: bool = False,
                        file_name: str = None) -> None:
    """Copy or update a file between source and replica."""
    source_size = get_file_size(source_file)
    source_mod_date = get_file_modification_date(source_file)

    replica_size = None
    replica_mod_date = None

    if os.path.exists(replica_file):
        replica_size = get_file_size(replica_file)
        replica_mod_date = get_file_modification_date(replica_file)

    try:
        shutil.copy2(source_file, replica_file)
        if is_update:
            log_message(log_file_path,
                        f"File '{file_name}' modified since last sync. "
                        f"Updated file: {source_file} -> {clean_log_path}. "
                        f"Size: {replica_size} -> {source_size} bytes. "
                        f"Date: {replica_mod_date} -> {source_mod_date}")
        else:
            log_message(log_file_path, f"Copied new file: {source_file} -> {clean_log_path}")
        changes[0] += 1
    except PermissionError:
        log_error(log_file_path, "PermissionError", source_file, replica_file, "copy/update")
    except OSError as e:
        log_error(log_file_path, e, source_file, replica_file, "copy/update")


def create_folder(replica_path: str, log_file_path: str, changes: list) -> None:
    """Create a folder in the replica directory."""
    try:
        os.makedirs(replica_path)
        log_message(log_file_path, f"Created folder '{replica_path}'")
        changes[1] += 1
    except PermissionError:
        log_error(log_file_path, "PermissionError", None, replica_path, "create")
    except OSError as e:
        log_error(log_file_path, e, None, replica_path, "create")


def create_or_update_files_and_folders(source_dir: str, replica_dir: str, log_file_path: str, changes: list) -> None:
    """Create or update files and folders in the replica directory."""
    for root, dirs, files in os.walk(source_dir):
        relative_path = os.path.relpath(root, source_dir)
        replica_path = os.path.join(replica_dir, relative_path)

        if not os.path.exists(replica_path):
            create_folder(replica_path, log_file_path, changes)

        for file_name in files:
            source_file = os.path.join(root, file_name)
            replica_file = os.path.join(replica_path, file_name)
            clean_log_path = replica_file.replace(replica_dir + os.sep + ".", replica_dir)

            if not os.path.exists(replica_file):
                copy_or_update_file(source_file, replica_file, clean_log_path, log_file_path, changes)
            else:
                source_mtime = os.path.getmtime(source_file)
                replica_mtime = os.path.getmtime(replica_file)

                if source_mtime != replica_mtime or calculate_sha1(source_file) != calculate_sha1(replica_file):
                    copy_or_update_file(source_file, replica_file, clean_log_path, log_file_path, changes,
                                        is_update=True, file_name=file_name)


def delete_file(replica_file: str, log_file_path: str, changes: list) -> None:
    """Delete a file from the replica directory."""
    try:
        os.remove(replica_file)
        log_message(log_file_path, f"Deleted file '{replica_file}'")
        changes[0] += 1
    except PermissionError:
        log_error(log_file_path, "PermissionError", None, replica_file, "delete")
    except OSError as e:
        log_error(log_file_path, e, None, replica_file, "delete")


def delete_folder(replica_subdir: str, log_file_path: str, changes: list) -> None:
    """Delete a folder from the replica directory."""
    try:
        changes_in_dir = [0, 0]

        for root, dirs, files in os.walk(replica_subdir):
            changes_in_dir[0] += len(files)
            changes_in_dir[1] += len(dirs)

        changes[0] += changes_in_dir[0]
        changes[1] += changes_in_dir[1]

        shutil.rmtree(replica_subdir)
        log_message(log_file_path,
                    f"Deleted folder '{replica_subdir}' and {changes_in_dir[0]} files inside it, "
                    f"including {changes_in_dir[1]} subfolders")
        changes[1] += 1
    except PermissionError:
        log_error(log_file_path, "PermissionError", None, replica_subdir, "delete")
    except OSError as e:
        log_error(log_file_path, e, None, replica_subdir, "delete")


def remove_deleted_files_and_folders(source_dir: str, replica_dir: str, log_file_path: str, changes: list) -> None:
    """Remove deleted files and folders from the replica directory."""
    for root, dirs, files in os.walk(replica_dir):
        relative_path = os.path.relpath(root, replica_dir)
        source_path = os.path.join(source_dir, relative_path)

        for file_name in files:
            replica_file = os.path.join(root, file_name)
            source_file = os.path.join(source_path, file_name)

            if not os.path.exists(source_file):
                delete_file(replica_file, log_file_path, changes)

        for dir_name in dirs:
            replica_subdir = os.path.join(root, dir_name)
            source_subdir = os.path.join(source_path, dir_name)

            if not os.path.exists(source_subdir):
                delete_folder(replica_subdir, log_file_path, changes)


def sync_folders(source_dir: str, replica_dir: str, log_file_path: str, interval: int, stop_event: Event) -> None:
    """Synchronize the replica folder with the source folder in a loop."""
    while not stop_event.is_set():
        start_time = time.time()

        log_message(log_file_path, f"Start synchronization process '{source_dir}' -> '{replica_dir}'...")
        changes = [0, 0]
        create_or_update_files_and_folders(source_dir, replica_dir, log_file_path, changes)
        remove_deleted_files_and_folders(source_dir, replica_dir, log_file_path, changes)

        end_time = time.time()
        time_taken = end_time - start_time

        log_message(log_file_path,
                    f"Synchronization completed: {changes[0]} files and {changes[1]} folders were changed "
                    f"in {time_taken:.2f} seconds.")
        log_message(log_file_path, "***")

        if stop_event.wait(int(interval)):
            break


def main() -> None:
    """Main function to periodically synchronize folders."""
    args = sys.argv[1:]

    try:
        source_dir, replica_dir, interval = args
    except ValueError:
        print("Please input source dir path, replica dir path and interval for synchronization.")
        sys.exit(1)

    check_input(source_dir, replica_dir, interval)

    log_file_path = get_log_file_path(os.getcwd())
    log_message(
        log_file_path, f"Run synchronization algorithm with parameters '{source_dir}, {replica_dir}, {interval}'\n***"
    )

    stop_event = Event()

    sync_thread = threading.Thread(
        target=sync_folders, args=(source_dir, replica_dir, log_file_path, interval, stop_event)
    )
    sync_thread.start()

    try:
        while sync_thread.is_alive():
            sync_thread.join(1)
    except KeyboardInterrupt:
        stop_event.set()
        sync_thread.join()
        log_message(log_file_path, "Synchronization process stopped.")


if __name__ == "__main__":
    main()
