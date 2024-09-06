# data-synchronization

## Introduction
This script synchronizes the contents of two directories: a source directory and a replica directory. The program copies files and folders from the source directory to the replica, updates existing files, and deletes obsolete files in the replica that no longer exist in the source. Every operation performed by the program is logged in a log file for detailed tracking.

## How to Run
To run the program, use the following command:

```bash
python main.py source replica 60
```
Where:

* `source` is the path to the source directory that needs to be synchronized.
* `replica` is the directory where files from the source will be copied.
* `60` is the interval in seconds for how often the synchronization will happen.

Example: To synchronize the folders C:\my_folder and C:\backup_folder every 60 seconds:

```bash
python main.py C:\my_folder C:\backup_folder 60
```

## Main Functions
The code is divided into functions, each handling a specific task to keep the program clear and maintainable.

* File and Folder Operations: The program creates folders in the replica, copies or updates files by detecting changes using SHA-1, and removes files or folders from the replica if they no longer exist in the source.

* Logging and Error Handling: The program tracks and logs all files and folders processed (created, updated, or deleted) during each sync cycle. Errors that can appear during file operations are logged, but the program continues running to avoid interrupting the sync process.


## Multithreading
The program uses multithreading to run the synchronization process in the background:

* `sync_thread` is a thread where the synchronization process runs. This allows the main program to remain responsive and handle interruptions (like Ctrl+C).

* `stop_event` controls when the program should stop. If the user interrupts the process, the stop_event ensures the sync thread can exit gracefully without leaving any unfinished operations.

<hr>
The code needs to be optimized for different time intervals and sizes of synchronized data.
