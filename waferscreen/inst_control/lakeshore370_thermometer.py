'''
A thermometer for a Lakeshore 370
'''

class Lakeshore370Thermometer(object):
    def __init__(self, address, name, lakeshore):
        # Lakeshore address (1-16)
        self.address = address
        # Decription of the thermometer
        self.name = name
        self.lakeshore = lakeshore
