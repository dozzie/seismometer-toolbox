#!/usr/bin/python

from setuptools import setup, find_packages
from glob import glob

setup(
    name         = 'seismometer-toolbox',
    version      = '0.3.0',
    description  = "Small tools for Seismometer",
    scripts      = glob("bin/*"),
    packages     = find_packages("lib"),
    package_dir  = { "": "lib" },
)
