from collections import UserDict
from waferscreen.analyze.table_read import num_format

allowed_meta_data_types = (str, float, int)
raw_filename_key = "output_filename"
metadata_primary_types = {"utc", "path"}


def metadata_key_format(key):
    string_key = str(key)
    return string_key.strip().lower()


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
            if isinstance(formatted_value, allowed_meta_data_types):
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
        return "# Metadata:," + return_str[:-1]
