#!/usr/bin/env python

import os
try:
    from ez_setup import use_setuptools
    use_setuptools()
except ImportError:
    pass

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='acomms',
    version='0.7.0',
    author='Eric Gallimore, Andrew Beal',
    author_email='pyacomms@whoi.edu',
    packages=['acomms', 'acomms.modem_connections', 'bin',],
    url='http://acomms.whoi.edu/',
    license='LGPLv3+',
    description='WHOI Micromodem Interface Library and Tools',
    long_description=read('README.txt'),
    install_requires=[
        "bitstring >= 3.0.0",
        "pyserial >= 2.6",
        "isodate >= 0.4.9",
        "python-dateutil >= 2.1",
        "timer2 >= 0.1.0",
        "enum >= 0.4.4",
        "apscheduler>=2.1.1",
        "crcmod>=1.7"
    ],
    py_modules=['ez_setup'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering",
    ],
)

