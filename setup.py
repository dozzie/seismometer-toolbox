#!/usr/bin/python

from setuptools import setup, find_packages
from glob import glob

version = open('version').readline().strip().replace('v', '')

setup(
  name         = 'seismometer-toolbox',
  version      = version,
  description  = "Small tools for Seismometer",
  scripts      = glob("bin/*"),
  packages     = find_packages("lib"),
  package_dir  = { "": "lib" },
)
