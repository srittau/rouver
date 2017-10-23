#!/usr/bin/python

import os

from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="rouver",
    version="0.3.1",
    description="A microframework",
    long_description=read("README.rst"),
    author="Sebastian Rittau",
    author_email="srittau@rittau.biz",
    url="https://github.com/srittau/rouver",
    packages=["rouver", "rouver_test"],
    install_requires=["werkzeug >= 0.12.0"],
    tests_require=["asserts >= 0.7.0, < 0.8"],
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
    ]
)
