import datetime
import math
from ref import umux_screener_assembly_path


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
                    value = raw_box_metadata[(2 * n) + 1]
                    box_metadata[key] = value
                current_box_number = box_metadata["boxnumber"]
                all_boxes_dict[current_box_number] = {"boxmetadata": box_metadata, "positions_dicts": {}}
            # check for box position to get the box position header
            elif "boxposition" in s_line:
                box_position_header = [column_name for column_name in row_data if column_name != ""]
            # the default mode is to expect box position data
            else:
                parsed_position_data = [value for value in row_data if value != ""]
                # make dictionary
                position_dict = {column_name: value for column_name, value in
                                 zip(box_position_header, parsed_position_data)}
                box_position = position_dict["boxposition"]
                all_boxes_dict[current_box_number]["positions_dicts"][box_position] = position_dict
    return all_boxes_dict


def parse_for_waferscreen(path):
    a_chain_packaging = None
    b_chain_packaging = None
    all_boxes_dict = read_umux_screener(path)
    for boxnumber in all_boxes_dict.keys():
        rf_chain_letter = all_boxes_dict[boxnumber]["boxmetadata"]["rfchain"]
        if rf_chain_letter == "a":
            a_chain_packaging = all_boxes_dict[boxnumber]
        elif rf_chain_letter == "b":
            b_chain_packaging = all_boxes_dict[boxnumber]
    return a_chain_packaging, b_chain_packaging


if __name__ == "__main__":
    # full_path = "/Users/cwheeler/PycharmProjects/WaferScreen/waferscreen/umux_screener_assembly.csv"
    full_path = umux_screener_assembly_path
    a_chain_packaging, b_chain_packaging = parse_for_waferscreen(path=full_path)
