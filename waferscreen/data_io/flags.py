# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

from ref import flag_file_path
from typing import NamedTuple, Optional
from operator import attrgetter
from waferscreen.data_io.s21_metadata import num_format

flag_file_header = "wafer,band,res_num,type,note,seed_res_num,seed_name,user"
flag_file_item_list = flag_file_header.split(",")


class ResFlag(NamedTuple):
    wafer: int
    band: int
    res_num: int
    type: str
    note: Optional[str] = None
    seed_res_num: Optional[int] = None
    seed_name: Optional[str] = None
    user: Optional[str] = None

    def __str__(self):
        return_str = F"{self.__getattribute__(flag_file_item_list[0])}"
        for attr in flag_file_item_list[1:]:
            value = self.__getattribute__(attr)
            if isinstance(value, str) and "," in value:
                value = value.replace(',', "|")
            return_str += F",{value}"
        return return_str


class Flagger:
    def __init__(self):
        self.all_flags = None
        self.wafer_band_flags = None

    def read(self):
        with open(flag_file_path, 'r') as f:
            raw_file_text = [a_line.strip() for a_line in f.readlines()]
        header = raw_file_text[0].split(",")
        flag_lines = raw_file_text[1:]
        value_split_flag_lines = [[num_format(a_value.strip()) for a_value in flag_line.split(",")]
                                  for flag_line in flag_lines]
        flag_dicts = [{key: value for key, value in zip(header, flag_line)} for flag_line in value_split_flag_lines]
        self.all_flags = {ResFlag(**flag_dict) for flag_dict in flag_dicts}

    def write(self):
        with open(flag_file_path, 'w') as f:
            f.write(F"{flag_file_header}\n")
            for res_flag in sorted(self.all_flags, key=attrgetter("wafer", "band", "res_num")):
                f.write(F"{res_flag}\n")

    def organize(self):
        self.wafer_band_flags = {}
        for res_flag in self.all_flags:
            if res_flag.wafer not in self.wafer_band_flags.keys():
                self.wafer_band_flags[res_flag.wafer] = {}
            if res_flag.band not in self.wafer_band_flags[res_flag.wafer].keys():
                self.wafer_band_flags[res_flag.wafer][res_flag.band] = []
            self.wafer_band_flags[res_flag.wafer][res_flag.band].append(res_flag)

    def add(self, res_flags):
        if self.all_flags is None:
            self.all_flags = set()
        for res_flag in res_flags:
            self.all_flags.add(res_flag)
        if self.wafer_band_flags is not None:
            self.organize()


if __name__ == "__main__":
    wafer = 11
    user = "chw3k5"
    wafer11 = [{"band": 0, "res_num": 1, "type": "expected no flux ramp",
                "note": "As designed, this resonator is not connected to the flux ramp.",
                "seed_res_num": 1, "seed_name": "scan4.000GHz-4.500GHz_2021-02-12 05-48-00.492736"},
               {"band": 0, "res_num": 5, "type": "anomalous lambda",
                "note": "This resonator has an anomalous lambda curve",
                "seed_res_num": 5, "seed_name": "scan4.000GHz-4.500GHz_2021-02-12 05-48-00.492736"},
               {"band": 0, "res_num": 65, "type": "weak flux ramp",
                "note": "This resonator is weakly connected to the flux ramp line and is unusually out of band. This unfortunate space means that it will likely interfere with the resonators in band01",
                "seed_res_num": 65, "seed_name": "scan4.000GHz-4.500GHz_2021-02-12 05-48-00.492736"},
               {"band": 2, "res_num": 66 - 65, "type": "expected no flux ramp",
                "note": "As designed, this resonator is not connected to the flux ramp.",
                "seed_res_num": 66, "seed_name": "scan4.000GHz-4.500GHz_2021-02-12 05-48-00.492736"},
               {"band": 2, "res_num": 117 - 65, "type": "collision",
                "note": "This resonator is too close to its neighbor res 53",
                "seed_res_num": 117, "seed_name": "scan4.000GHz-4.500GHz_2021-02-12 05-48-00.492736"},
               {"band": 2, "res_num": 118 - 65, "type": "collision",
                "note": "This resonator is too close to its neighbor res 52",
                "seed_res_num": 118, "seed_name": "scan4.000GHz-4.500GHz_2021-02-12 05-48-00.492736"},
               {"band": 11, "res_num": 1, "type": "expected no flux ramp",
                "note": "As designed, this resonator is not connected to the flux ramp.",
                "seed_res_num": 1, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 11, "res_num": 2, "type": "no flux ramp",
                "note": "This resonator is not connected to the flux ramp line.",
                "seed_res_num": 2, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 11, "res_num": 33, "type": "no flux ramp",
                "note": "This resonator is not connected to the flux ramp line.",
                "seed_res_num": 33, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 11, "res_num": 34, "type": "weak flux ramp",
                "note": "This resonator is only weakly connected to the flux ramp line.",
                "seed_res_num": 34, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 11, "res_num": 49, "type": "no flux ramp",
                "note": "This resonator is not connected to the flux ramp line.",
                "seed_res_num": 49, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 11, "res_num": 49, "type": "no flux ramp",
                "note": "This resonator is not connected to the flux ramp line.",
                "seed_res_num": 49, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 11, "res_num": 51, "type": "collision",
                "note": "This resonator is too close to its neighbor res 52",
                "seed_res_num": 51, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 11, "res_num": 52, "type": "collision",
                "note": "This resonator is too close to its neighbor res 51",
                "seed_res_num": 52, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 13, "res_num": 66 - 65, "type": "expected no flux ramp",
                "note": "As designed, this resonator is not connected to the flux ramp.",
                "seed_res_num": 66, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 13, "res_num": 80 - 65, "type": "collision",
                "note": "The resonator required several upgrades to the proceeding code. It seems to be a double resonator, where one resonator is connected to the flux ramp and one resonator (or resonate feature) is static as the flux ramp is sweeped.",
                "seed_res_num": 80, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 13, "res_num": 118 - 65, "type": "anomalous lambda",
                "note": "Produced Lambda Fit curves that looked over powered, even at the nominal low input power. The plot below shows the failure of the fitter for such a resonator.",
                "seed_res_num": 118, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               {"band": 13, "res_num": 130 - 65, "type": "no flux ramp|isolated",
                "note": "This resonator is not connected to the flux ramp.",
                "seed_res_num": 130, "seed_name": "scan5.600GHz-6.100GHz_2021-02-11 19-12-14.079197"},
               ]

    wafer12 = [{"band": 0, "res_num": 1, "type": "expected no flux ramp",
                "note": "As designed, this resonator is not connected to the flux ramp.",
                "seed_res_num": 1, "seed_name": "scan3.900GHz-4.500GHz_2021-02-10 19-04-56.938380"},
               {"band": 2, "res_num": 66 - 65, "type": "expected no flux ramp",
                "note": "As designed, this resonator is not connected to the flux ramp.",
                "seed_res_num": 66, "seed_name": "scan3.900GHz-4.500GHz_2021-02-10 19-04-56.938380"},
               {"band": 11, "res_num": 1, "type": "expected no flux ramp",
                "note": "As designed, this resonator is not connected to the flux ramp.",
                "seed_res_num": 1, "seed_name": "scan5.500GHz-6.100GHz_2021-02-11 03-21-55.604930"},
               {"band": 13, "res_num": 67 - 66, "type": "expected no flux ramp",
                "note": "As designed, this resonator is not connected to the flux ramp.",
                "seed_res_num": 67, "seed_name": "scan5.500GHz-6.100GHz_2021-02-11 03-21-55.604930"},
               ]
    res_flags_to_add = []
    for res_dict in wafer11:
        res_dict.update({"wafer": 11, "user": user})
        res_flags_to_add.append(ResFlag(**res_dict))
    for res_dict in wafer12:
        res_dict.update({"wafer": 12, "user": user})
        res_flags_to_add.append(ResFlag(**res_dict))

    flagger = Flagger()
    flagger.add(res_flags=res_flags_to_add)
    flagger.organize()
    flagger.write()

