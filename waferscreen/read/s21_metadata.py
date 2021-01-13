import os
from collections import UserDict
from waferscreen.read.table_read import num_format
from ref import s21_metadata_nist

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
            formatted_datum = F"{key},{self.data[key]}|"
            # put utc first, the rest in alphabetical order
            if key in metadata_primary_types:
                return_str = formatted_datum + return_str
            else:
                return_str += formatted_datum
        # add prefix, get rid of the last comma ","
        return "# Metadata:" + return_str[:-1]


class S21MetadataPrinceton:
    def __init__(self):
        self.file_to_meta = {}
        self.paths = []

    def meta_from_file(self, path):
        with open(path, mode='r') as f:
            raw_file = f.readlines()
        for raw_line in raw_file:
            meta_data_this_line = {}
            key_value_phrases = raw_line.split("|")
            for key_value_phrase in key_value_phrases:
                key_str, value_str = key_value_phrase.split(",")
                meta_data_this_line[key_str.strip()] = num_format(value_str.strip())
            else:
                if "path" in meta_data_this_line.keys():
                    local_test_path = os.path.join(os.path.dirname(path), meta_data_this_line["path"])
                    if os.path.isfile(local_test_path):
                        meta_data_this_line["path"] = local_test_path
                    self.file_to_meta[meta_data_this_line["path"]] = meta_data_this_line
                else:
                    raise KeyError("No path. All S21 meta data requires a unique path to the S21 file.")
        self.paths.append(path)


class S21MetadataNist:
    def __init__(self):
        self.metadata_by_path = None

    def read(self, delimiter_major=",", delimiter_minor="|"):
        self.metadata_by_path = {}
        with open(s21_metadata_nist, "r") as f:
            for single_metadata_line in f:
                metadata_this_line = MetaDataDict()
                for key_value_phrase in single_metadata_line.split(delimiter_major):
                    raw_key, raw_value = key_value_phrase.split(delimiter_minor)
                    # normally would do more formatting to these stings,
                    # but in this case the MetaDataDict class does that for us does that
                    metadata_this_line[raw_key] = raw_value
                if raw_filename_key in metadata_this_line.keys():
                    raw_path = metadata_this_line[raw_filename_key]
                    self.metadata_by_path[raw_path] = metadata_this_line
                else:
                    raise KeyError(F"Required unique filename key, {raw_filename_key},\n" +
                                   "was not found")


    def hack_read(self, delimiter_major=",", delimiter_minor="="):
        self.metadata_by_path = {}
        with open(s21_metadata_nist, "r") as f:
            for single_metadata_line in f:
                metadata_this_line = {}
                for key_value_phrase in single_metadata_line.split(delimiter_major):
                    raw_key, raw_value = key_value_phrase.split(delimiter_minor)
                    metadata_this_line[raw_key.strip().lower()] = num_format(raw_value)
                if raw_filename_key in metadata_this_line.keys():
                    raw_path = metadata_this_line[raw_filename_key]
                    self.metadata_by_path[raw_path] = metadata_this_line


if __name__ == "__main__":
    s21_mdn = S21MetadataNist()
    s21_mdn.hack_read(delimiter_minor="=")






