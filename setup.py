from distutils.core import setup

setup(name='spexodisks',
      version='0.2.0',
      description='An Testing and Database infrastructure for the NIST-SO wafer production',
      author='Caleb Wheeler, Jake Connors',
      author_email='chw3k5@gmail.com',
      packages=['waferscreen'],
      requires=['numpy', 'matplotlib', 'scipy']
      )
