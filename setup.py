#!/usr/bin/python

from setuptools import setup


setup(
    name="rouver",
    version="0.1.0",
    description="A microframework",
    author="Sebastian Rittau",
    author_email="srittau@rittau.biz",
    url="https://github.com/srittau/rouver",
    packages=["rouver"],
    install_requires=["werkzeug >= 0.12.0"],
    tests_require=["asserts"],
)
