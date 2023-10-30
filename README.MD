# A pure Python module for recording and processing low-level Android input events (Mouse/Keyboard/Touchpad) - no dependencies

## pip install geteventplayback

### Tested against Windows 10 / Python 3.11 / Anaconda 

GeteventPlayBack is a powerful Python module that simplifies the capture and
processing of input events from Android devices, including not only touch events but also
mouse and keyboard events. It is designed to work entirely with native Python, making it
a versatile choice for Android input event analysis. 

### IMPORTANT: ONLY WORKS ON ROOTED DEVICES/EMULATORS

[![YT](https://i.ytimg.com/vi/LyGX7rQ-fLY/maxresdefault.jpg)](https://www.youtube.com/watch?v=LyGX7rQ-fLY)
[https://www.youtube.com/watch?v=LyGX7rQ-fLY]()

```python

"""
Args:
	adb_path (str): The path to the 'adb' tool.
	device (str): The device event file to record, e.g., "/dev/input/event3".
	device_serial (str): The serial number or address of the Android device.
	print_output (bool): Whether to print the 'getevent' output to the console.
	tmpfolder_device (str): The temporary folder on the device to store event data.
	tempfolder_hdd (str): The temporary folder on the local HDD to store event data.
	add_closing_command (bool): Whether to add closing commands to the event replay.
	clusterevents (int): The number of events to cluster together for replay, allowing
	you to adjust playback speed.

Methods:
	- start_recording(): Start recording input events, including mouse and keyboard events,
	  and customize the playback speed.
	- _get_files_and_cmd(unpacked_data): Process the recorded data and generate
	  commands for event replay.
	- _format_binary_data(): Format binary data from 'getevent' output into events.

Attributes:
	- alldata (list): The raw 'getevent' output data, stored as bytes.
	- FORMAT (str): The format string for parsing binary data.
	- chunk_size (int): The size of each event in bytes.
	- timestampnow (float): The current timestamp.
"""
	

import subprocess

from geteventplayback import GeteventPlayBack

pla = GeteventPlayBack(
    adb_path=r"C:\Android\android-sdk\platform-tools\adb.exe",
    device="/dev/input/event4",
    device_serial="127.0.0.1:5555",
    print_output=True,
    tmpfolder_device="/sdcard/event4/",
    tempfolder_hdd=rf"C:\sadxxxxxxxxxxxx",
    add_closing_command=True,
    clusterevents=16,
)

results = pla.start_recording()

subprocess.run(
    [pla.adb_path, "-s", pla.device_serial, "shell"],
    bufsize=0,
    input=results["adbcommand"],  # Can be resused
)

```
