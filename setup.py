#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2023 Trygve Aspenenes

# Author(s):

#   Trygve Aspenes <trygveas@met.no>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Setup for satellite schedule status promtheus.
"""
from setuptools import setup
import imp

version = imp.load_source(
    "satpy_pygeoapi_plugin.version", "satpy_pygeoapi_plugin/version.py"
)

setup(
    name="satpy_pygeoapi_plugin",
    version=version.__version__,
    description="SATPY pygeoapi plugin reading netcdf and mapscript",
    author="Trygve Aspenes",
    author_email="trygveas@met.no",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 "
        + "or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering",
    ],
    url="",
    packages=[
        "satpy_pygeoapi_plugin",
    ],
    scripts=[],
    data_files=[],
    zip_safe=False,
    install_requires=[
        "satpy",
    ],
    tests_require=[],
    test_suite="",
)
