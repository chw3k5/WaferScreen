from distutils.core import setup

setup(name='WaferScreen',
      version='1.0.2',
      description='Testing and database infrastructure for the NIST-SO wafer production',
      author='Caleb Wheeler, Zach Whipps, Johannes Hubmayr, Jordan Wheeler, Jake Connors',
      author_email='chw3k5@gmail.com',
      packages=['waferscreen'],
      requires=['numpy', 'matplotlib', 'scipy', "pyvisa", "LabJackPython", "PySerial", "numba"]
      )
