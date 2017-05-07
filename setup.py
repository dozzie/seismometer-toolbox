#!/usr/bin/python

from setuptools import setup, find_packages
from glob import glob

setup(
    name         = "seismometer-toolbox",
    version      = "0.5.0",
    description  = "Utilities for building monitoring systems",
    scripts      = glob("bin/*"),
    packages     = find_packages("lib"),
    package_dir  = { "": "lib" },
)
