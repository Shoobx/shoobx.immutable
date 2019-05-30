##############################################################################
#
# Copyright (c) 2011 Zope Foundation and Contributors.
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
"""Doc Tests"""

import doctest
import unittest

OPTIONFLAGS = (
    doctest.NORMALIZE_WHITESPACE|
    doctest.ELLIPSIS|
    doctest.REPORT_ONLY_FIRST_FAILURE
    )


def test_suite():
    suite = unittest.TestSuite((
        doctest.DocFileSuite(
            '../README.rst',
            #setUp=setUp, tearDown=tearDown,
            optionflags=OPTIONFLAGS
        )
    ))
    return suite
