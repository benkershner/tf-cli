#!/usr/bin/env python

from setuptools import setup

requires = ['requests>=2.0']

setup(name='pytf',
      version='0.2',
      description='2lemetry ThingFabric Command Line Interface',
      url='http://github.com/benkershner/tf-cli',
      author='Ben Kershner',
      author_email='ben.kershner@gmail.com',
      license='MIT',
      packages=['pytf'],
      install_requires=requires,
      scripts=['bin/tf'],
      zip_safe=False)
