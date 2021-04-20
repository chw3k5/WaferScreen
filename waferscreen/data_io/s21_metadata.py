# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

from collections import UserDict

allowed_meta_data_types = (str, float, int)
raw_filename_key = "output_filename"
metadata_primary_types = {"utc", "path"}
forbidden_characters = {"|", ","}


def num_format(a_string):
    if isinstance(a_string, int):
        # it is an int
        return a_string
    elif isinstance(a_string, float):
        # it is either and float or a string

        int_version = int(a_string)
        float_version = float(a_string)
        if int_version == float_version:
            # check if it really should be an int
            return int_version
        else:
            # it was already a float or a string representing a float
            return float_version
    else:
        try:
            return int(a_string)
        except ValueError:
            try:
                return float(a_string)
            except ValueError:
                # this can only be represented as a string
                return a_string.strip()


def metadata_key_format(key):
    string_key = str(key)
    formatted_string_key = string_key.strip().lower()
    for letter in formatted_string_key:
        if letter in forbidden_characters:
            raise TypeError(F"The characters {forbidden_characters} are not allowed for metadata keys.")
    return formatted_string_key


class MetaDataDict(UserDict):
    def __missing__(self, key):
        if isinstance(key, str):
            raise KeyError
        return self[metadata_key_format(key)]

    def __contains__(self, key):
        return str(key) in self.data

    def __setitem__(self, key, value):
        formatted_key = metadata_key_format(key)
        if self.__contains__(formatted_key):
            formatted_value = num_format(value)
            if formatted_value != self.data[formatted_key]:
                raise KeyError("An attempt was made to set a key-value pair for which the key " +
                               F"'{formatted_key}'\n is already set to value {self.data[formatted_key]}\n" +
                               F"different from the value, {formatted_value}, that was attempted to be set.\n" +
                               "This is not allowed, and may indicate a mistake in the metadata system")
        else:
            formatted_value = num_format(value)
            if isinstance(formatted_value, str):
                for letter in formatted_value:
                    if letter in forbidden_characters:
                        raise TypeError(F"The characters {forbidden_characters} are not allowed for metadata values.")
                self.data[formatted_key] = formatted_value
            elif isinstance(formatted_value, allowed_meta_data_types):
                self.data[formatted_key] = formatted_value
            else:
                raise TypeError("The MetaDataDict only excepts values of the following types: " +
                                F"{allowed_meta_data_types}\nHowever value of {formatted_value} was encountered.")

    def __str__(self):
        return_str = ""
        for key in sorted(self.keys()):
            formatted_datum = F"{key}|{self.data[key]},"
            # put utc first, the rest in alphabetical order
            if key in metadata_primary_types:
                return_str = formatted_datum + return_str
            else:
                return_str += formatted_datum
        # add prefix, get rid of the last comma ","
        return "# Metadata:" + return_str[:-1]
