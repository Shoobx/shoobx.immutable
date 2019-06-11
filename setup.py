##############################################################################
#
# Copyright (c) 2019 Shoobx, Inc.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Setup
"""
import os
from setuptools import setup, find_packages

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

def alltests():
    import os
    import sys
    import unittest
    # use the zope.testrunner machinery to find all the
    # test suites we've put under ourselves
    import zope.testrunner.find
    import zope.testrunner.options
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
    args = sys.argv[:]
    defaults = ["--test-path", here]
    options = zope.testrunner.options.get_options(args, defaults)
    suites = list(zope.testrunner.find.find_suites(options))
    return unittest.TestSuite(suites)

TESTS_REQUIRE = [
    'coverage',
    'mock',
    'pjpersist[test]',
    'zope.testrunner',
    ]

setup (
    name="shoobx.immutable",
    version='1.1.1',
    author="Shoobx, Inc.",
    author_email="dev@shoobx.com",
    description="Immutable Types",
    long_description=(
        read('README.rst')
        + '\n\n' +
        read('docs', 'README.rst')
        + '\n\n' +
        read('CHANGES.rst')
        ),
    license="ZPL 2.1",
    keywords="immutable revisioned pjpersist",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Natural Language :: English',
        'Operating System :: OS Independent'],
    url='http://pypi.python.org/pypi/shoobx.immutable',
    packages=find_packages('src'),
    package_dir={'':'src'},
    namespace_packages=['shoobx'],
    extras_require=dict(
        docs=[
            'Sphinx',
            'repoze.sphinx.autointerface'
        ],
        pjpersist=[
            'pjpersist',
        ],
        test=TESTS_REQUIRE,
    ),
    install_requires=[
        'setuptools',
        'zope.component',
        'zope.interface',
        'zope.lifecycleevent',
        'zope.schema',
    ],
    tests_require=TESTS_REQUIRE,
    test_suite='__main__.alltests',
    include_package_data=True,
    zip_safe=False,
    )
