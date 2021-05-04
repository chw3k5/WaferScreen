# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.
import os
import numpy as np
from datetime import datetime
from pytz.reference import Mountain  # The local time zone on the computer logging data
from operator import itemgetter
from typing import NamedTuple
from ref import starcryo_logs_dir


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


def get_and_dat_organize_log_files(logs_dir):
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

        for_sorting.append((log_datetime, log_file_full_path))
    # Sort the file and time list based on the times.
    sorted_times_and_paths = sorted(for_sorting, key=itemgetter(0), reverse=True)
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
    # get all the log file name
    sorted_logs = get_and_dat_organize_log_files(logs_dir=logs_dir)
    # get all the log entries for each data file
    log_entries = []
    [log_entries.extend(get_log_data_from_file(log_path)) for _log_datetime, log_path in sorted_logs]
    return log_entries


def get_most_recent_log_entries(logs_dir=None):
    if logs_dir is None:
        logs_dir = starcryo_logs_dir
    # get all the log file name
    sorted_logs = get_and_dat_organize_log_files(logs_dir=logs_dir)
    # get all the log entries for the most recent log file
    most_recent_log = sorted_logs[0]
    return get_log_data_from_file(log_path=most_recent_log)


if __name__ == "__main__":
    log_entries = get_all_log_entries()
