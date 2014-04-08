#!/usr/bin/python

from setuptools import setup, find_packages

setup(
  name         = 'panopticon-toolbox',
  version      = '0.0.1',
  description  = "Small tools for Panopticon",
  packages     = find_packages("lib"),
  package_dir  = { "": "lib" },
)
