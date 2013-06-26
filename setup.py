__author__ = "rread"

from setuptools import setup, find_packages
import dyner53

setup(name='dyner53',
      version=dyner53.__version__,
      description='Dynamic Route53 Updater',
      author='Robert Read',
      author_email='robertread@gmail.com',
      url='https://github.com/rread/dyner53',
      packages=find_packages(),
      install_requires=open('requirements.txt').readlines(),
      license='PSF',
      entry_points={
          'console_scripts': [
              'dyner53 = dyner53.main:main',
          ]
      },
)
