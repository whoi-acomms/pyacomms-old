#!/usr/bin/env python

from distutils.core import setup
import shutil

#Examples in SRC directory
FileList = [
"bottomnode.py",
"ctd.py",
"dispatcher.py",
"dropbottle.py",
"ducertest.py",
"excepttest.py",
"glider.py",
"gliderlisten.py",
"glidertx.py",
"gwbuoy.py",
"main.py",
"spare.py",
"vfinbottle.py",
"bottomnode.py",
"ctd.py",
"dispatcher.py",
"dropbottle.py",
"ducertest.py",
"excepttest.py",
"glider.py",
"gliderlisten.py",
"glidertx.py",
"gwbuoy.py",
"main.py",
"spare.py",
"vfinbottle.py"
]

ScriptList = []

#Move them to the example directory
for file in FileList:
	shutil.move("src/%s"%file,"bin/.")
	ScriptList.append("bin/%d")

print ScriptList
exit

setup(
    name='MicroModem',
    version='1.0',
    author='Eric Gallimore, Andrew Beal',
    author_email='abeal@whoi.edu',
    packages=['Micromodem'],
	package_dir={'':'src'},
	scripts=ScriptList,
    url='http://acomms.whoi.edu/',
    license='LICENSE.txt',
    description='Micromodem Python Tool.',
    long_description=open('README.txt').read(),
    install_requires=[
        "bitstring >= 3.0.0",
        "pyserial >= 2.7",
    ],
)

