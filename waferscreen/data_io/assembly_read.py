''' assembly_read.py

parse data from umux_screener_assembly_hannes into wafer screen data structure.
wafer screen data structure is organized by microwave chain, is a dictionary with keys:

'boxmetadata':
    'packagestateon' : datetime.date
    'boxnumber': str
    'packagedby': str
    'assemblydate': str
    'umuxdesign': str
    'rfchain': str

'positions_dicts':
    'a1' -> 'a4'
    'b1' -> 'b4' with keys:
        'boxposition': (same as the key?)
        'wafer': str
        'band': str
        'x_position': str
        'y_position': str

Notes:
1) wafer screen data structure assumes that 4 ports of a umux screener package are
always ganged together.
2) switched 'x(y)_position' to 'row' 'column' to synch with nist QSG standard
3) add keys to metadata:
    'electricalprobing':{'a':'cpw thru','fr','fr_to_gnd','cpw_to_gnd'}
4) currently only handles one package in one file.

'''
import datetime

def read_assembly_spreadsheet(path):
    # read all the lines into a list
    with open(path, 'r') as f:
        raw_lines = f.readlines()

    raw_lines = remove_eol(raw_lines)

    d_dict = {'boxmetadata':{},'positions_dicts':{}}

    for ii, line in enumerate(raw_lines):
        if raw_lines[0] == '#' or raw_lines[0] == ' ':
            pass
        parse_row = line.split(',')
        if 'Assembly Date:' in parse_row[0]:
            d_dict['boxmetadata']['assemblydate'] = str(parse_row[1])
            d_dict['boxmetadata']['packagestateon'] = datetime.datetime.strptime(str(parse_row[1]).replace(",", "").strip(),"%Y-%m-%d").date()
        if 'Packaged by:' in parse_row[0]:
            d_dict['boxmetadata']['packagedby'] = str(parse_row[1])
        if 'Device box #:' in parse_row[0]:
            d_dict['boxmetadata']['boxnumber'] = str(parse_row[1])
        if 'Mux version:' in parse_row[0]:
            d_dict['boxmetadata']['umuxdesign'] = str(parse_row[1])
        if parse_row[0] == '!!!!!':
            rf_chain, positions_dicts, eprobe_dict = parse_device_box_assembly(raw_lines[ii:ii+3])
            break
    d_dict['boxmetadata']['electricalprobing']=eprobe_dict
    d_dict['boxmetadata']['rfchain']=rf_chain
    d_dict['positions_dicts'] = positions_dicts
    return d_dict

def remove_eol(raw_lines):
    for ii, line in enumerate(raw_lines):
        if line[-1] == '\n':
            raw_lines[ii] = line[:-1]
    return raw_lines

def parse_device_box_assembly(devbox_raw_lines):
    # input is a 3x10 spreadsheet of cells
    d_list = []
    positions_dicts={}
    for line in devbox_raw_lines:
        d_list.append(line.split(','))

    rf_chain = get_rf_chain(d_list)
    # map chips to package locations and microwave chain
    for ii in range(1,2): # rows
        devbox_row = make_lower_case(d_list[1][0])
        for jj in range(1,5): # columns
            row, column, wafer, band = parse_chip_id(d_list[ii][jj])
            positions_dicts[devbox_row+str(jj)] = {'wafer':wafer, 'row':row, 'column':column, 'band':band, 'boxposition':devbox_row+str(jj)}
    eprobe_dict = parse_electrical_probing(d_list) # parse the room temp electrical probing separately

    return rf_chain, positions_dicts, eprobe_dict, # in future may wish to return devbox_row_a and devbox_row_b separately if on different microwave chains

def get_rf_chain(devbox_list):
    rf_chain_index = devbox_list[0].index('rf chain (a or b)')
    assert devbox_list[1][rf_chain_index] == devbox_list[2][rf_chain_index], 'You have an 8 chip packaged coupled to two different rf chains. Are you crazy?'
    return devbox_list[1][rf_chain_index]

def parse_electrical_probing(devbox_list):
    eprobe_dict = {}
    for ii in range(1,3): # row index
        devbox_row = make_lower_case(devbox_list[ii][0])
        eprobe_dict[devbox_row] ={}
        for jj in range(6,10): # column index
            #print(devbox_row, devbox_list[ii][jj])
            eprobe_dict[devbox_row][devbox_list[0][jj]] = devbox_list[ii][jj]
    return eprobe_dict

def make_lower_case(val):
    x=None
    if val =='A' or val=='a': x='a'
    elif val =='B' or val=='b': x='b'
    else:
        print('unknown microwave chain',val)
    return x

def parse_chip_id(id_str):
    row, column, wafer, band = id_str.split(':')
    return row, column, wafer, band

if __name__ == "__main__":
    path = "umux_screener_assembly_example.csv"
    d_dict = read_assembly_spreadsheet(path)
    print(d_dict)
