#!/usr/bin/env python

import os
import subprocess
import shutil
import sys
import setuptools

parent_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

INSTALL_REQUIRES = ['python-dateutil']
if sys.version_info < (2, 6):
    # The 'json' module is included with Python 2.6+
    INSTALL_REQUIRES.append('simplejson')
    INSTALL_REQUIRES.append('ssl')  # This module is built in to Python 2.6+

extra = {}
if sys.version_info >= (3,):
    extra['use_2to3'] = True

    # convert the test code to Python 3
    # because distribute won't do that for us
    # first copy over the tests
    tests_dir = os.path.join(parent_dir, "tests")
    tests3_dir = os.path.join(parent_dir, "3tests")
    if 'test' in sys.argv and os.path.exists(tests_dir):
        shutil.rmtree(tests3_dir, ignore_errors=True)
        shutil.copytree(tests_dir, tests3_dir)
        subprocess.call(["2to3", "-w", "--no-diffs", tests3_dir])
    TEST_SUITE = '3tests'
else:
    TEST_SUITE = 'tests'

setuptools.setup(
    name='dropbox2',
    version='1.7.1',
    description='Dropbox REST API Client with more consistent responses.',
    author='Rick van Hattem',
    author_email='Rick@Wol.ph',
    url='http://wol.ph/',
    packages=['dropbox', 'tests'],
    install_requires=INSTALL_REQUIRES,
    package_data={'dropbox': ['trusted-certs.crt'],
                  'tests': ['server.crt', 'server.key']},
    test_suite=TEST_SUITE,
    tests_require=['mock'],
    **extra
)

