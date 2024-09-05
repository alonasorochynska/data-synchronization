import os
import shutil
import sys
import time
import hashlib
from datetime import datetime


class FolderNotFoundError(Exception):
    pass


def calculate_md5(file_path):  # check this!!!!!!!!!!!
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_log_file_path(log_dir):
    return os.path.join(log_dir, "sync_logs.log")


def log_message(log_file_path, message):
    """Log a message to the log file and print to the console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    with open(log_file_path, "a") as file:
        if message == "***":
            file.write(message + "\n")
        else:
            file.write(log_entry + "\n")
    print(log_entry)


def check_input(source_dir, replica_dir, interval):
    if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
        raise FolderNotFoundError(f"Source dir '{source_dir}' does not exist!")

    if not os.path.exists(replica_dir) or not os.path.isdir(replica_dir):
        raise FolderNotFoundError(f"Replica dir '{replica_dir}' does not exist!")

    try:
        int(interval)
    except ValueError:
        print("Interval must be an integer.")
        sys.exit(1)


def get_file_size(file_path):
    return os.path.getsize(file_path)


def get_file_modification_date(file_path):
    mod_timestamp = os.path.getmtime(file_path)
    mod_date = datetime.fromtimestamp(mod_timestamp)
    return mod_date.strftime('%Y-%m-%d %H:%M:%S')


def create_or_update_files(source_dir, replica_dir, log_file_path):
    for root, dirs, files in os.walk(source_dir):
        relative_path = os.path.relpath(root, source_dir)
        replica_path = os.path.join(replica_dir, relative_path)

        if not os.path.exists(replica_path):
            os.makedirs(replica_path)
            log_message(log_file_path, f"Created folder '{replica_path}'")

        for file_name in files:
            source_file = os.path.join(root, file_name)
            replica_file = os.path.join(replica_path, file_name)
            clean_log_path = replica_file.replace(replica_dir + os.sep + '.', replica_dir)

            if not os.path.exists(replica_file):
                shutil.copy2(source_file, replica_file)
                log_message(log_file_path, f"Copied new file: {source_file} -> {clean_log_path}")

            elif calculate_md5(source_file) != calculate_md5(replica_file):
                source_size = get_file_size(source_file)
                replica_size = get_file_size(replica_file)

                source_mod_date = get_file_modification_date(source_file)
                replica_mod_date = get_file_modification_date(replica_file)

                shutil.copy2(source_file, replica_file)

                log_message(
                    log_file_path,
                    f"File '{file_name}' modified since last sync. "
                    f"Updated file: {source_file} -> {clean_log_path}. "
                    f"Size: {replica_size} -> {source_size} bytes. "
                    f"Date: {replica_mod_date} -> {source_mod_date}"
                )


def remove_deleted_files_and_folders(source_dir, replica_dir, log_file_path):
    """Remove files and folders"""
    for root, dirs, files in os.walk(replica_dir):
        relative_path = os.path.relpath(root, replica_dir)
        source_path = os.path.join(source_dir, relative_path)

        for file_name in files:
            replica_file = os.path.join(root, file_name)
            source_file = os.path.join(source_path, file_name)

            if not os.path.exists(source_file):
                os.remove(replica_file)
                log_message(log_file_path, f"Deleted file '{replica_file}'")

        for dir_name in dirs:
            replica_subdir = os.path.join(root, dir_name)
            source_subdir = os.path.join(source_path, dir_name)

            if not os.path.exists(source_subdir):
                shutil.rmtree(replica_subdir)
                log_message(log_file_path, f"Deleted folder '{replica_subdir}'")


def sync_folders(source_dir, replica_dir, log_file_path):
    """Synchronize the replica folder with the source folder."""

    create_or_update_files(source_dir, replica_dir, log_file_path)
    remove_deleted_files_and_folders(source_dir, replica_dir, log_file_path)


def main():
    """Main function to periodically synchronize folders."""
    args = sys.argv[1:]

    try:
        source_dir, replica_dir, interval = args
    except ValueError:
        print("Please input source dir path, replica dir path and interval for synchronization.")
        sys.exit(1)

    check_input(source_dir, replica_dir, interval)

    log_file_path = get_log_file_path(os.getcwd())
    log_message(log_file_path, f"Run synchronization algorithm with parameters '{source_dir}, {replica_dir}, {interval}'\n***")

    while True:
        log_message(log_file_path, "Starting synchronization...")
        sync_folders(source_dir, replica_dir, log_file_path)
        log_message(log_file_path, "Synchronization completed.")
        log_message(log_file_path, "***")
        time.sleep(int(interval))


if __name__ == "__main__":
    main()
