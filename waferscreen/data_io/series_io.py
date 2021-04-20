# Copyright (C) 2021 Members of the Simons Observatory collaboration.
# Please refer to the LICENSE file in the root of this repository.

from typing import NamedTuple


class SeriesKey(NamedTuple):
    port_power_dbm: float
    if_bw_hz: float

    def __str__(self):
        return F"portPowerdBm{'%5.1f' % self.port_power_dbm}_ifbwHz{'%08i' % self.if_bw_hz}"


series_key_header = list(SeriesKey._fields)
