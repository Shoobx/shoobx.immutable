=======================================
``shoobx.immutable`` -- Immutable Types
=======================================

.. image:: https://travis-ci.org/Shoobx/shoobx.immutable.png?branch=master
   :target: https://travis-ci.org/Shoobx/shoobx.immutable

.. image:: https://coveralls.io/repos/github/Shoobx/shoobx.immutable/badge.svg?branch=master
   :target: https://coveralls.io/github/Shoobx/shoobx.immutable?branch=master

.. image:: https://img.shields.io/pypi/v/shoobx.immutable.svg
    :target: https://pypi.python.org/pypi/shoobx.immutable

.. image:: https://img.shields.io/pypi/pyversions/shoobx.immutable.svg
    :target: https://pypi.python.org/pypi/shoobx.immutable/

.. image:: https://readthedocs.org/projects/shoobximmutable/badge/?version=latest
        :target: http://shoobximmutable.readthedocs.org/en/latest/
        :alt: Documentation Status

This library provides a state-based implementation of immutable types,
including lists, sets and dicts. It handles an arbitrarily deep structure of
nested objects.

In addition, support for revisioned immutables is provided, which allows for
full revision histories of an immutable. A sample implementation of a
revisioned immutable maanger is also provided.

Optional: A pjpersist-based storage mechanism for revisioned immutables is
provided, which allows for easy storage of versioned immutables.
