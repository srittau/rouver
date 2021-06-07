#!/usr/bin/env python

import os

from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="rouver",
    version="2.4.0",
    description="A microframework",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Sebastian Rittau",
    author_email="srittau@rittau.biz",
    url="https://github.com/srittau/rouver",
    packages=["rouver", "rouver_test"],
    package_data={"rouver": ["py.typed"]},
    install_requires=["dectest >= 1.0.0, < 2", "werkzeug >= 0.16.0, werkzeug < 3"],
    tests_require=["asserts >= 0.10.0, < 0.12"],
    python_requires=">= 3.7",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
    ],
)
