# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.
import os
import time
import bisect
from collections import deque
from datetime import datetime, timedelta
from operator import attrgetter
from typing import NamedTuple
from threading import Thread, Event
from shutil import copyfile
import numpy as np
from pytz.reference import Mountain  # The local time zone on the computer logging data
from ref import starcryo_logs_dir, earliest_log, project_starcryo_logs_dir


class StarCryoLogFile(NamedTuple):
    path: str
    log_type: str
    datetime: datetime


class StarCryoLogEntry(NamedTuple):
    timestamp: datetime
    test_time: float
    log_comments: str
    ps_v: float
    sim960v: float
    ps_i: float
    rleads: float
    pressure: float
    tset: float
    snout_coil_set: float
    adr_50mk: float
    pt_60k: float
    pt_3k: float
    magnet_diode: float
    auxiliary: float
    adr_1k: float
    magnet_rtd: float
    h20_inlet_temp: float
    h20_outlet_temp: float
    helium_temp: float
    oil_temp: float
    high_side_press: float
    low_side_press: float
    current: float
    runtime_min: float
    sim921_r: float
    sim922_1_v: float
    sim922_2_v: float
    sim922_3_v: float
    sim922_4_v: float
    sim923a1_r: float
    sim923a2_r: float


def get_and_organize_log_files(logs_dir):
    """


    :param logs_dir:
    :return list:
    """
    # test for and remove the .txt extension
    all_log_files = [log_file_candidate[:-4] for log_file_candidate in os.listdir(logs_dir)
                     if log_file_candidate[-4:] == ".txt"]
    # do the parsing and collect the data for sorting
    for_sorting = []
    for log_file_basename in all_log_files:
        log_file_full_path = os.path.join(logs_dir, F"{log_file_basename}.txt")
        log_type, date_str, time_str = log_file_basename.split("-")
        month_str, day_str, year_str = date_str.split("_")
        hour_str, min_str, sec_str = time_str.split("_")
        # time object is useful for sorting
        log_datetime = datetime(year=int(year_str), month=int(month_str), day=int(day_str),
                                hour=int(hour_str), minute=int(min_str), second=int(sec_str),
                                tzinfo=Mountain)
        file_record = StarCryoLogFile(path=log_file_full_path, datetime=log_datetime, log_type=log_type.lower())
        for_sorting.append(file_record)
    # Sort the file and time list based on the times.
    sorted_times_and_paths = sorted(for_sorting, key=attrgetter('datetime'), reverse=True)
    return sorted_times_and_paths


def get_log_data_from_file(log_path):
    # get all raw text from the log file
    with open(log_path, 'r') as f:
        raw_lines = [raw_line.strip() for raw_line in f.readlines()]
    # the first line is the header info, all the headers are the same so this information is in StarCryoLogEntry
    # get the log entries, one per row
    log_entries = []
    for raw_line in raw_lines[1:]:
        try:
            # the first column needs to be formatted as a datetime object, 3rd is a str, the rest are floats
            entry_datetime, entry_test_time, entry_log_comments, *entry_float_strs = raw_line.split(',')
        except ValueError:
            # Sometime the file is not properly terminated, due to power outages or whatever. We can move on
            pass
        # only finish this lab of the loop if the data unpacks correctly
        else:
            # parse the datatime str from the log
            date_str, time_str = entry_datetime.split(" ")
            month_str, day_str, year_str = date_str.split("/")
            hour_str, min_str, sec_str = time_str.split(":")
            whole_sec_str, decimal_sec_str = sec_str.split(".")
            micro_sec = int(np.round(float("0." + decimal_sec_str) * 1.0e6))
            entry_datetime = datetime(year=int(year_str), month=int(month_str), day=int(day_str),
                                      hour=int(hour_str), minute=int(min_str), second=int(whole_sec_str),
                                      microsecond=micro_sec, tzinfo=Mountain)
            # turn the rest of the data entries to floats
            entry_floats = [float(entry_float) for entry_float in entry_float_strs]
            # put the parsed data in the StarCryoLogEntry and append it to log
            log_entries.append(StarCryoLogEntry(entry_datetime, float(entry_test_time), entry_log_comments,
                                                *entry_floats))
    # we want the most recent data at the top of the list, so we reverse the list here
    log_entries.reverse()
    return log_entries


def get_all_log_entries(logs_dir=None):
    """
    Get evey single log entry that is available for the StarCryo system.

    Warning: this could be a lot of data, 3.9 GB and growing as of May 4th, 2021

    :param logs_dir: None or the the full path of the directory that contains the StarCryo Log file. None selects
                     the default path specified in variable 'starcryo_logs_dir' in the ref.py file
                     located in the root directory of this repository.
    :return: list containing log entries that objects of StarCryoLogEntry, a sub-class of NamedTuple.
             See the class "StarCryoLogEntry" formatting details.
    """
    if logs_dir is None:
        logs_dir = starcryo_logs_dir
    # get all the log file names
    sorted_logs = get_and_organize_log_files(logs_dir=logs_dir)
    # get all the log entries for each data file
    log_entries = []
    [log_entries.extend(get_log_data_from_file(file_record.path)) for file_record in sorted_logs]
    return log_entries


def get_most_recent_log_entries(logs_dir=None):
    if logs_dir is None:
        logs_dir = starcryo_logs_dir
    # get all the log file names
    sorted_logs = get_and_organize_log_files(logs_dir=logs_dir)
    # get all the log entries for the most recent log file
    most_recent_log = sorted_logs[0]
    return get_log_data_from_file(log_path=most_recent_log)


class Monitor:
    def __init__(self):
        self.sleep_time_s = 10
        self.most_recent_log_path = None
        self.most_recent_log_datetime = None
        self.most_recent_log_type = None
        self.is_in_regulation = Event()
        self._stop_event = Event()

    def get_most_recent_log_filename(self):
        sorted_logs = get_and_organize_log_files(logs_dir=starcryo_logs_dir)
        log_record = sorted_logs[0]
        self.most_recent_log_path = log_record.path
        self.most_recent_log_type = log_record.log_type
        self.most_recent_log_datetime = log_record.datetime
        if self.most_recent_log_type == 'regul':
            return self.is_in_regulation.set()
        else:
            return self.is_in_regulation.clear()

    def log_check(self):
        while not self.is_log_check_stopped():
            self.get_most_recent_log_filename()
            time.sleep(self.sleep_time_s)
        print("StarCryo Log Monitoring Finished.")

    def in_regulation(self):
        if self.most_recent_log_type == 'regul':
            return self.is_in_regulation.set()
        else:
            return self.is_in_regulation.clear()

    def check_regulation_status(self):
        return self.is_in_regulation.is_set()

    def stop_log_check(self):
        self._stop_event.set()

    def is_log_check_stopped(self):
        return self._stop_event.is_set()


def log_checker(monitor_obj):
    monitor_obj.log_check()


def measurement_simulator(monitor, loops=100, sleep=5):
    for loop_index in range(loops):
        if monitor.is_in_regulation.is_set():
            print(F"In regulation - Measuring")
        else:
            print(F"Out of regulation - Measurements Paused")
        time.sleep(sleep)


class StarCryoData:
    record_return_cutoff_seconds = 5.0

    def __init__(self, logs_dir=None):
        if logs_dir is None:
            logs_dir = starcryo_logs_dir
        self.starcryo_file_info = get_and_organize_log_files(logs_dir=logs_dir)
        self.starcryo_file_info_unread = deque(self.starcryo_file_info[:])
        self.history_begin_datetime = datetime(9999, 12, 31, 23, 59, 59, 999999, Mountain)
        # Newest records are delivered first.
        self.raw_records_reversed = []
        # In order of increasing values order is needed for the bisect method
        self.raw_records = None
        self.time_stamps = None

    def read_records(self, utc=None):
        if utc is None:
            self.raw_records_reversed = get_all_log_entries(logs_dir=None)
        else:
            for log_path, log_type, log_start_time in list(self.starcryo_file_info_unread):
                self.raw_records_reversed.extend(get_log_data_from_file(log_path=log_path))
                self.starcryo_file_info_unread.popleft()
                self.history_begin_datetime = self.raw_records_reversed[-1].timestamp
                if log_start_time < utc:
                    break
        # In order of increasing values order is needed for the bisect method
        self.raw_records = list(reversed(self.raw_records_reversed))
        self.time_stamps = [rec.timestamp for rec in self.raw_records]

    def get_record(self, utc, verbose=True):
        found_record = None
        # dynamically read in data you need, going back as far as necessary in history to retive the request record
        if utc < self.history_begin_datetime:
            self.read_records(utc=utc)
        # do the binary search for the record index
        time_stamps_right_index = bisect.bisect(a=self.time_stamps, x=utc)
        # get the record index to the right of the requested tim
        time_stamps_left_index = time_stamps_right_index - 1
        # a few calculations
        rec_right = self.raw_records[time_stamps_right_index]
        rec_left = self.raw_records[time_stamps_left_index]
        dt_right = utc - rec_right.timestamp
        dt_left = rec_left.timestamp - utc
        # the records need to be within the self.record_return_cutoff_seconds of the requested time to be returned
        if dt_right < timedelta(seconds=self.record_return_cutoff_seconds) \
                or dt_left < timedelta(seconds=self.record_return_cutoff_seconds):
            # choose what record is closer
            if dt_right < dt_left:
                found_record = rec_right
            else:
                found_record = rec_left
        else:
            if verbose:
                print(F"\nNo StarCryo Log records within {self.record_return_cutoff_seconds} seconds of the")
                print(F"requested time: {utc})")
                print(F" left (after) record delta t: {dt_left}")
                print(F"right (before) record delta t: {dt_right}")
        return found_record


# this is only True on the data logging computer
if project_starcryo_logs_dir != starcryo_logs_dir:
    # import log files into the git repository.
    logs_originals = get_and_organize_log_files(logs_dir=starcryo_logs_dir)
    logs_basenames_originals = {os.path.basename(log_path) for log_path, log_type, log_start_time in logs_originals}
    # find the files already saved in this project
    logs_project = get_and_organize_log_files(logs_dir=project_starcryo_logs_dir)
    logs_basenames_project = {os.path.basename(log_path) for log_path, log_type, log_start_time in logs_project}
    # calculate which files are new
    logs_basenames_new = logs_basenames_originals - logs_basenames_project
    # always re-copy the latest file project, it may have been committed at an incomplete state
    if logs_project:
        logs_basenames_new.add(os.path.basename(logs_project[0][0]))
    files_to_add = set()
    for original_log_path, original_log_type, original_log_start_time in logs_originals:
        original_basename = os.path.basename(original_log_path)
        if original_basename in logs_basenames_new and earliest_log < original_log_start_time \
                and original_log_type == 'regul':
            source_path = os.path.join(starcryo_logs_dir, original_basename)
            destination_path = os.path.join(project_starcryo_logs_dir, original_basename)
            files_to_add.add((source_path, destination_path))
    if 1 < len(files_to_add):
        for source_path, destination_path in files_to_add:
            # copy the file to the projects folder
            copyfile(source_path, destination_path)
            # add the new files to the git repository
            os.system(F"git add {destination_path}")
            print(F"git add for StarCryo Log File:{destination_path}")
        # commit the files that have been added if there is at least 2 files
        os.system('''git commit -m "Automatically added star cryo log files."''')
        print(F"git commit -m 'Automatically added star cryo log files'")


if __name__ == "__main__":
    get_all_logs_records = False
    monitor_thead_test = False
    get_log_record = True
    # datetime(year, month, day, hour, minute, second, microsecond)
    request_time = datetime(2021, 4, 13, 6, 0, 0, 0, Mountain)

    if get_all_logs_records:
        all_log_entries = get_all_log_entries()

    if monitor_thead_test:
        a_monitor = Monitor()
        a_monitor.get_most_recent_log_filename()
        t = Thread(target=log_checker, args=(a_monitor, ))
        t.start()
        measurement_simulator(a_monitor, loops=100, sleep=5)

    if get_log_record:
        star_cryo_data = StarCryoData()
        requested_record = star_cryo_data.get_record(utc=request_time)
