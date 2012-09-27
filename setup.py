#!/usr/bin/env python

from distutils.core import setup
from ez_setup import use_setuptools
    
use_setuptools()

setup(
    name='MicroModem',
    version='1.0',
    author='Eric Gallimore, Andrew Beal',
    author_email='abeal@whoi.edu',
    packages=['Micromodem'],
	package_dir={'Micromodem':'src'},
    url='http://acomms.whoi.edu/',
    license='LICENSE.txt',
    description='Micromodem Python Tool.',
    long_description=open('README.txt').read(),
    install_requires=[
        "bitstring >= 3.0.0",
        "pyserial >= 2.6",
    ],
)

