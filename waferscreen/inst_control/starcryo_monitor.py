# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.
import os
import time
from datetime import datetime
from operator import attrgetter
from typing import NamedTuple
from threading import Thread, Event

import numpy as np
from pytz.reference import Mountain  # The local time zone on the computer logging data
from ref import starcryo_logs_dir


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
        # time object is useful for comparson and sorting
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
        print("StarCryo Log Monitoring finished.")

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


if __name__ == "__main__":
    # log_entries = get_all_log_entries()
    monitor = Monitor()
    monitor.get_most_recent_log_filename()
    t = Thread(target=log_checker, args=(monitor, ))
    t.start()
    measurement_simulator(monitor, loops=100, sleep=5)

