from distutils.core import setup

setup(name='WaferScreen',
      version='1.1.2',
      description='Testing and database infrastructure for the NIST-SO wafer production',
      author='Caleb Wheeler, Zach Whipps, Johannes Hubmayr, Jordan Wheeler, Jake Connors',
      author_email='chw3k5@gmail.com',
      packages=['waferscreen', "gluerobot", "submm_python_routines"],
      url="https://github.com/chw3k5/WaferScreen",
      requires=['numpy', 'matplotlib', 'scipy', "pyvisa", "LabJackPython", "PySerial", "numba",
                'pytz', 'pyqt5', 'pandas']
      )
