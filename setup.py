from distutils.core import setup

setup(name='WaferScreen',
      version='0.1.0',
      description='Testing and database infrastructure for the NIST-SO wafer production',
      author='Caleb Wheeler, Jake Connors',
      author_email='chw3k5@gmail.com',
      packages=['waferscreen'],
      requires=['numpy', 'matplotlib', 'scipy', "pyvisa", "LabJackPython", "PyAutoGUI", "PySerial"]
      )
