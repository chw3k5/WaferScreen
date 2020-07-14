"""
This file read-in file for data is tailored to replace the the "atpy" packages read-in functionally.

1) How ever there are some differences: Comment lines denoted by a "#" are now saved to a 'comments' in a
   dictionary key or object attribute.
2) All blank lines, or lines of only white space are ignored.
3) All numbers are by default converted to floats.
4) Only columns that are all integers will be converted to integers, candidate integer items in columns of
   integers mixed with floats or strings will remain as floats.
"""


def num_format(a_string):
    try:
        return int(a_string)
    except ValueError:
        try:
            return float(a_string)
        except ValueError:
            return a_string


def get_table_data(filename, delimiter=','):
    """
    Get Data and comments from a file.
    returns a dictionary object contain any comments and the columns of data in a file.
    The headers of the columns used as the dictionary key to access the column data in the dictionary.
    """
    # set defaults
    column_header_found = False
    table_dict = {"comments": []}
    # open the file for reading
    f = open(filename, 'r')
    # read file line-by-line
    for line in f:
        if line.strip() == "":
            """
            We will not be needing any blank lines, this catch will stop them fom being passed as data or comments
            """
            pass
        elif line[0] == "#":
            """
            Some files have header data the is commented out be the "#"
            First we will identify those lines and save them in a "comments" dictionary 
            """
            # we can strip off the "#" and any white space or "\n" characters from the end of the comment
            comment_line = line.replace("#", "", 1).strip()
            # we append to the the comments section of the dictionary
            if comment_line != "":
                table_dict["comments"].append(comment_line)
        elif not column_header_found:
            """
            The first uncommented non-blank line is assumed to be the column header names
            """
            # turn on the flag to start reading in data on the next line
            column_header_found = True
            # get the column names
            column_names = line.strip().split(delimiter)
            for column_name in column_names:
                table_dict[column_name] = []
        else:
            """
            Now that we are into the table data we will map one the items in a row to the correct column of data
            """
            row_items = line.split(delimiter)
            for (index, row_item) in list(enumerate(row_items)):
                # Get rid of white space, "\n", and "\r" characters
                stripped_item = row_item.strip()
                # if item is a number convert it to a float
                processed_item = num_format(stripped_item)
                # assign the item to the correct column name in tableDct
                table_dict[column_names[index]].append(processed_item)
    # The is no need for a blank comments section of this dictionary
    if not table_dict["comments"]:
        del table_dict["comments"]
    """
    We will check to see if the data in a column is all integers or not.
    If it is all integers in a column of data then we will convert that column from floats to integers. 
    """
    for key in column_names:
        all_items_are_integers = True
        integer_column = []
        for item in table_dict[key]:
            if type(item) is int:
                integer_column.append(int(item))
            else:
                all_items_are_integers = False
                break
        if all_items_are_integers:
            table_dict[key] = integer_column
    return table_dict


def row_dict(filename, key=None, delimiter=",", null_value=None, inner_key_remove=True):
    """
    Use this to make a dictionary of dictionaries per row of data in a table. The outer most dictionary has keys set
    from the column of data listed under the header denoted be the "key" parameter. The inner dictionary contains the
    row data, keys are the headers for that column of data.

    :param filename: a string of the filename of the table to be read.
    :param key: the row header of the row that will be the keys for the outer most dictionary. if key == None, a list
                of dictionaries is generated.
    :param delimiter: the delimiter of the the data in the table being read in.
    :param null_value: if this value is in the table, skip writing it to the dictionary.
    :return: a dictionary of dictionaries
    """
    table_dict = get_table_data(filename=filename, delimiter=delimiter)
    keys = list(table_dict.keys())
    if "comments" in keys:
        comments = table_dict["comments"]
        keys.remove("comments")
    else:
        comments = None
    if key is None:
        data_len = len(table_dict[keys[0]])
        if null_value is None:
            data = [{key: table_dict[key][row_index] for key in keys} for row_index in range(data_len)]
        else:
            data = [{key: table_dict[key][row_index] for key in keys if table_dict[key][row_index] != null_value}
                    for row_index in range(data_len)]
    else:
        if key not in keys:
            raise ValueError("The specified key: " + str(key) + " is not in the set of keys: " + str(keys) +
                             " \nfor the table: " + str(filename))
        else:
            if inner_key_remove:
                keys.remove(key)
            if null_value is None:
                data = {outer_key: {inner_key: table_dict[inner_key][row_index] for inner_key in keys}
                        for row_index, outer_key in list(enumerate(table_dict[key]))}
            else:
                data = {outer_key: {inner_key: table_dict[inner_key][row_index] for inner_key in keys
                                    if table_dict[inner_key][row_index] != null_value}
                        for row_index, outer_key in list(enumerate(table_dict[key]))}
    if comments is not None:
        data["comments"] = comments
    return data


class ClassyReader:
    """
    Use this class if you want to access your data as an attribute to a class obj and not a dictionary.
    To see the attributes in which you data is stored, use the keys attribute.
    One added functionally over the table dictionary definition above is the that the filename from which the data
    is read, is also saved under the filename attribute.
    """
    def __init__(self, filename, delimiter=","):
        self.filename = filename
        table_dict = get_table_data(filename=filename, delimiter=delimiter)
        self.keys = list(table_dict.keys())
        for key in self.keys:
            setattr(self, key, table_dict[key])


if __name__ == "__main__":
    Zenoviene14 = ClassyReader(filename="abundance_data/zenoviene14.csv")
    battistini15 = ClassyReader(filename="abundance_data/battistini15.tsv", delimiter="|")
    print("done")
