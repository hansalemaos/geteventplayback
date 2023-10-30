import ctypes
import os
import sys
import tempfile
import threading
import time
import subprocess
from functools import partial
import struct


def list_split(l, indices_or_sections):
    Ntotal = len(l)
    try:
        Nsections = len(indices_or_sections) + 1
        div_points = [0] + list(indices_or_sections) + [Ntotal]
    except TypeError:
        Nsections = int(indices_or_sections)
        if Nsections <= 0:
            raise ValueError("number sections must be larger than 0.") from None
        Neach_section, extras = divmod(Ntotal, Nsections)
        section_sizes = (
            [0] + extras * [Neach_section + 1] + (Nsections - extras) * [Neach_section]
        )
        div_points = []
        new_sum = 0
        for i in section_sizes:
            new_sum += i
            div_points.append(new_sum)

    sub_arys = []
    lenar = len(l)
    for i in range(Nsections):
        st = div_points[i]
        end = div_points[i + 1]
        if st >= lenar:
            break
        sub_arys.append((l[st:end]))

    return sub_arys


def killthread(threadobject):
    # based on https://pypi.org/project/kthread/
    if not threadobject.is_alive():
        return True
    tid = -1
    for tid1, tobj in threading._active.items():
        if tobj is threadobject:
            tid = tid1
            break
    if tid == -1:
        sys.stderr.write(f"{threadobject} not found")
        return False
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(tid), ctypes.py_object(SystemExit)
    )
    if res == 0:
        return False
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
        return False
    return True


class GeteventPlayBack:
    def __init__(
        self,
        adb_path,
        device,
        device_serial,
        print_output,
        tmpfolder_device,
        tempfolder_hdd,
        add_closing_command=True,
        clusterevents=16,
    ):
        r"""
        A class for recording and processing events using 'getevent' on an Android device.

        This class allows you to capture input events from an Android device and save them
        for further analysis. It can cluster the recorded events into groups, save them to
        the device, and generate commands for replaying the events.

        Args:
            adb_path (str): The path to the 'adb' tool.
            device (str): The device event file to record, e.g., "/dev/input/event3".
            device_serial (str): The serial number or address of the Android device.
            print_output (bool): Whether to print the 'getevent' output to the console.
            tmpfolder_device (str): The temporary folder on the device to store event data.
            tempfolder_hdd (str): The temporary folder on the local HDD to store event data.
            add_closing_command (bool): Whether to add closing commands to the event replay.
            clusterevents (int): The number of events to cluster together for replay.

        Methods:
            - start_recording(): Start recording events and stop when the user presses ENTER.
            - _get_files_and_cmd(unpacked_data): Process the recorded data and generate
              commands for event replay.
            - _format_binary_data(): Format binary data from 'getevent' output into events.

        Attributes:
            - alldata (list): The raw 'getevent' output data.
            - FORMAT (str): The format string for parsing binary data.
            - chunk_size (int): The size of each event in bytes.
            - timestampnow (float): The current timestamp.
        """
        self.adb_path = adb_path
        self.device = device
        self.device_serial = device_serial
        self.alldata = []
        self.print_output = print_output
        self.pr = None
        self.FORMAT = "llHHI"
        self.chunk_size = struct.calcsize(self.FORMAT)
        self.timestampnow = time.time()
        self.clusterevents = clusterevents
        self.tmpfolder_device = tmpfolder_device
        self.tempfolder_hdd = tempfolder_hdd
        self.add_closing_command = add_closing_command
        os.makedirs(tempfolder_hdd, exist_ok=True)

    def _read_stdout(
        self,
        pr,
    ):
        try:
            for l in iter(pr.stdout.readline, b""):
                if self.print_output:
                    print(l)
                self.alldata.append(l)
        except Exception:
            try:
                self.pr.stdout.close()
            except Exception as fe:
                sys.stderr.write(f"{fe}")
                sys.stderr.flush()

    def start_recording(self):
        r"""
        Start recording input events from the Android device.

        This method launches the 'getevent' command on the specified device and begins
        capturing input events. Recording continues until the user presses ENTER in the
        console. The captured events are processed and grouped into clusters, and their
        binary data is saved to the local HDD and the device.

        Returns:
            dict: A dictionary containing parsed event data and commands for replay.
                The dictionary has the following keys:
                - 'parseddata': The parsed event data.
                - 'singleevents': List of individual events.
                - 'clusteredevents': Events grouped into clusters.
                - 'filesnames_pc': List of paths to binary data files on the local HDD.
                - 'adbcommand': A command to replay events on the device.
                - 'payload': All byte data captured during the recording.
        """
        try:
            pr = subprocess.Popen(
                f"{self.adb_path} -s {self.device_serial} shell su -- cat {self.device}",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                bufsize=0,
            )
            t3 = threading.Thread(target=self._read_stdout, kwargs={"pr": pr})
            t3.start()
            input("Press ENTER to stop")
            killall(
                pr,
                t3,
            )
        except Exception as fe:
            sys.stderr.write(f"{fe}")
            sys.stderr.flush()
        unpacked_data = self._format_binary_data()
        finalresults = self._get_files_and_cmd(unpacked_data)
        return finalresults

    def _get_files_and_cmd(self, unpacked_data):
        close2timestamp = []
        self.timestampnow = time.time()
        parseddata = [
            x
            for ini, x in enumerate(unpacked_data)
            if (
                x[0][0] > self.timestampnow * 0.95
                and close2timestamp.append(ini) is None
            )
            or x
        ]
        singleevents = list_split(l=parseddata, indices_or_sections=close2timestamp)
        singleevents = [x for x in singleevents if x]
        clusteredevents = list_split(
            singleevents, len(singleevents) // self.clusterevents
        )
        clusteredevents = [x for x in clusteredevents if x]

        subprocess.run(
            f"{self.adb_path} -s {self.device_serial} shell",
            input=b"mkdir -p " + self.tmpfolder_device.encode() + b"\n",
            bufsize=0,
        )

        filesnamepc = []
        adbcommands = []
        allbytedata = []
        for ini, groupevents in enumerate(clusteredevents):
            binarydata = []
            tmpfilenamehdd = os.path.join(self.tempfolder_hdd, str(ini) + ".bin")
            filesnamepc.append(tmpfilenamehdd)
            for each_event in groupevents:
                if not each_event:
                    continue
                for evi in each_event:
                    try:
                        binarydata.append(evi[5])
                    except Exception as fe:
                        binarydata.append(evi[0][5])
            joinedbin = b"".join(binarydata)
            allbytedata.extend(joinedbin)
            with open(tmpfilenamehdd, mode="wb") as f:
                f.write(joinedbin)
            subprocess.run(
                [
                    self.adb_path,
                    "-s",
                    self.device_serial,
                    "push",
                    tmpfilenamehdd,
                    self.tmpfolder_device,
                ],
                bufsize=0,
            )
            adbcommands.append(
                f"dd bs={(len(joinedbin))} if={self.tmpfolder_device}{ini}.bin of={self.device}"
            )

        if self.add_closing_command:
            adbcommands.extend(
                [
                    f"sendevent {self.device} 0 0 0",
                    f"sendevent {self.device} 0 2 0",
                    f"sendevent {self.device} 0 0 0",
                ]
            )

        return {
            "parseddata": parseddata,
            "singleevents": singleevents,
            "clusteredevents": clusteredevents,
            "filesnames_pc": filesnamepc,
            "adbcommand": (b"su -- " + ("\n".join(adbcommands)).encode()),
            "payload": allbytedata,
        }

    def _format_binary_data(self):
        sample_data = b"".join(self.alldata).replace(b"\r\n", b"\n")
        sample_data = sample_data[
            : (divmod(len(sample_data), self.chunk_size)[0] * self.chunk_size)
        ]
        allbytedata = []
        unpacked_data = [
            [struct.unpack(self.FORMAT, g) + (g,)]
            if not allbytedata.append((g := sample_data[i : i + self.chunk_size]))
            else None
            for i in range(0, len(sample_data), self.chunk_size)
        ]
        return unpacked_data


def killall(*args):
    for arg in args:
        try:
            arg.kill()
        except Exception:
            try:
                killthread(arg)
            except Exception:
                pass


def get_tmpfile(suffix=".txt"):
    tfp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    filename = tfp.name
    filename = os.path.normpath(filename)
    tfp.close()
    purefile = filename.split(os.sep)[-1]
    return purefile, filename, partial(os.remove, tfp.name)


#
def tempfolder():
    tempfolder = tempfile.TemporaryDirectory()
    tempfolder.cleanup()
    if not os.path.exists(tempfolder.name):
        os.makedirs(tempfolder.name)

    return (tempfolder.name,)
