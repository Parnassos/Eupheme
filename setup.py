#!/usr/bin/env python3

from setuptools import setup

setup(
    name='Eupheme',
    version='0.0.1',
    test_suite='tests',
    packages=['eupheme'],
    install_requires=['jinja2', 'Logbook', 'pyyaml']
)
