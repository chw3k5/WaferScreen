from waferscreen.data_io.data_pro import DataManager


def to_raw_path(seed_name):
    return F"{seed_name}.csv"


def dm_if_none(dm=None):
    if dm is None:
        return DataManager(user_input_group_delay=None)
    return dm

