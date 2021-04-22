# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

import datetime
import math
from ref import umux_screener_assembly_path
from waferscreen.data_io.s21_metadata import num_format, MetaDataDict


def read_umux_screener(path):
    # initialize the variables to return to screening program
    package_state_date = None
    box_position_header = None
    all_boxes_dict = {}
    current_box_number = -1
    # read all the lines into a list
    with open(path, 'r') as f:
        raw_lines = f.readlines()
    # strip off spaces and the newlines characters, make all the letters lowercase, get rid of white space
    stripped_lines = [a_line.strip().lower().replace(" ", "") for a_line in raw_lines]
    # Start the data parsing
    for s_line in stripped_lines:
        # ignore comment charters
        if not s_line[0] == "#" and not s_line[0:2] == '"#':
            # split the data
            row_data = s_line.split(",")
            # skip blank lines
            if row_data == len(row_data) * [""]:
                pass
            # check for package state date data
            elif "packagestateon:" in s_line:
                _, package_state_date_str = s_line.split(":", 1)
                package_state_date = datetime.datetime.strptime(package_state_date_str.replace(",", "").strip(),
                                                                "%Y-%m-%d").date()
            # check for box number metadata
            elif "boxnumber:" in s_line:
                box_metadata = {"packagestateon": package_state_date}
                raw_box_metadata = s_line.split(",")
                for n in range(math.floor(len(raw_box_metadata) / 2.0)):
                    key = raw_box_metadata[2 * n].replace(":", "")
                    value = num_format(raw_box_metadata[(2 * n) + 1])
                    box_metadata[key] = value
                current_box_number = box_metadata["boxnumber"]
                all_boxes_dict[current_box_number] = {"boxmetadata": box_metadata, "positions_dicts": {}}
            # check for box position to get the box position header
            elif "boxposition" in s_line:
                box_position_header = [column_name for column_name in row_data if column_name != ""]
            # the default mode is to expect box position data
            else:
                parsed_position_data = [num_format(value) for value in row_data if value != ""]
                # make dictionary
                position_dict = {column_name: value for column_name, value in
                                 zip(box_position_header, parsed_position_data)}
                box_position = position_dict["boxposition"]
                all_boxes_dict[current_box_number]["positions_dicts"][box_position] = position_dict
    return all_boxes_dict


def parse_for_waferscreen(all_boxes_dict):
    a_chain_packaging = None
    b_chain_packaging = None
    for boxnumber in all_boxes_dict.keys():
        rf_chain_letter = all_boxes_dict[boxnumber]["boxmetadata"]["rfchain"]
        if rf_chain_letter == "a":
            a_chain_packaging = all_boxes_dict[boxnumber]
        elif rf_chain_letter == "b":
            b_chain_packaging = all_boxes_dict[boxnumber]
    return a_chain_packaging, b_chain_packaging


class ScreenerSheet:
    def __init__(self, path=None):
        if path is None:
            self.path = umux_screener_assembly_path
        else:
            self.path = path
        self.all_boxes_dict = read_umux_screener(path=self.path)
        self.a_chain_packaging, self.b_chain_packaging \
            = parse_for_waferscreen(all_boxes_dict=self.all_boxes_dict)
        self.a_chain_by_band = None
        self.b_chain_by_band = None
        self.a_chain_wafers = None
        self.b_chain_wafers = None
        self.wafers_this_cool_down = None
        self.sort()

    def sort(self):
        self.a_chain_by_band = None
        self.b_chain_by_band = None
        # resort the data for method calls
        for chain_packaging in [self.a_chain_packaging, self.b_chain_packaging]:
            box_metadata = chain_packaging["boxmetadata"]
            rf_chain_letter = box_metadata["rfchain"]
            self.__setattr__(F"{rf_chain_letter}_chain_by_band", {})
            del box_metadata["rfchain"]
            positions_dicts = chain_packaging["positions_dicts"]
            self.__setattr__(F"{rf_chain_letter}_chain_wafers", set())
            wafers_this_chain = self.__getattribute__(F"{rf_chain_letter}_chain_wafers")
            for box_position in positions_dicts.keys():
                position_dict = positions_dicts[box_position]
                band = position_dict["band"]
                del position_dict["band"]
                box_and_pos_metadata = MetaDataDict(box_metadata)
                box_and_pos_metadata.update(position_dict)
                self.__getattribute__(F"{rf_chain_letter}_chain_by_band")[band] = box_and_pos_metadata
                wafers_this_chain.add(box_and_pos_metadata["wafer"])
            else:
                if len(wafers_this_chain) == 1:
                    self.__setattr__(F"{rf_chain_letter}_chain_wafers", list(wafers_this_chain)[0])
        # get all the wafers this cool down.
        wafers_this_cool_down = set()
        for rf_chain_letter in {"a", "b"}:
            wafers_this_chain = self.__getattribute__(F"{rf_chain_letter}_chain_wafers")
            if isinstance(wafers_this_chain, set):
                [wafers_this_cool_down.add(a_wafer) for a_wafer in wafers_this_chain]
            else:
                wafers_this_cool_down.add(wafers_this_chain)
        if len(wafers_this_cool_down) == 1:
            self.wafers_this_cool_down = list(wafers_this_cool_down)[0]

    def chain_and_band_to_package_data(self, rf_chain_letter, band_int):
        return self.__getattribute__(F"{rf_chain_letter.lower()}_chain_packaging")[band_int]

    def chain_to_wafer_number(self, rf_chain_letter):
        return self.__getattribute__(F"{rf_chain_letter}_chain_wafers")


# full_path = "/Users/cwheeler/PycharmProjects/WaferScreen/waferscreen/umux_screener_assembly.csv"
screener_sheet = ScreenerSheet()

