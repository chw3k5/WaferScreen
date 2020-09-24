import numpy as np
import os
from operator import itemgetter


def jordan_to_starcryo(file, new_file_name=None, delimiter=','):
    with open(file, 'r') as f:
        raw_lines = f.readlines()
    data = [tuple(single_line.rstrip().split(delimiter)) for single_line in raw_lines]
    by_column_data = list(zip(*data))
    by_column_floats = [np.array(data_column, dtype=float) for data_column in by_column_data]

    if new_file_name is None:
        basename = os.path.basename(file)
        path = os.path.dirname(file)
        new_file_name = os.path.join(path, "new_" + basename)

    with open(new_file_name, "w") as f:
        for res_omhs, temp_K in sorted(list(zip(by_column_floats[1], by_column_floats[0])), key=itemgetter(0)):
            f.write(F"{res_omhs}\t{temp_K}\n")


if __name__ == "__main__":
    jordan_to_starcryo(file="C:\\Users\\uvwave\\Downloads\\4990.txt",
                       new_file_name="C:\\Users\\uvwave\\Downloads\\Jordan_RuOx_4990.txt")
    jordan_to_starcryo(file="C:\\Users\\uvwave\\Downloads\\4993.txt",
                       new_file_name="C:\\Users\\uvwave\\Downloads\\Jordan_RuOx_4993.txt")
