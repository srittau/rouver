#!/usr/bin/env python

import os

from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="rouver",
    version="0.10.9",
    description="A microframework",
    long_description=read("README.rst"),
    author="Sebastian Rittau",
    author_email="srittau@rittau.biz",
    url="https://github.com/srittau/rouver",
    packages=["rouver", "rouver_test"],
    package_data={"rouver": ["py.typed"]},
    install_requires=[
        "dectest >= 1.0.0, < 2",
        "werkzeug >= 0.12.0",
    ],
    tests_require=["asserts >= 0.8.5, < 0.9"],
    python_requires=">= 3.5",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
    ])
