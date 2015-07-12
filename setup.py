#!/usr/bin/python

from setuptools import setup, find_packages
from glob import glob

setup(
    name         = 'seismometer-toolbox',
    version      = '0.0.0', # unspecified at this branch
    description  = "Small tools for Seismometer",
    scripts      = glob("bin/*"),
    packages     = find_packages("lib"),
    package_dir  = { "": "lib" },
)
