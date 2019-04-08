from setuptools import setup

setup(
    name = "yangson",
    packages = ["yangson"],
    use_scm_version = True,
    setup_requires=["setuptools_scm"],
    description = "Library for working with data modelled in YANG",
    author = "Ladislav Lhotka",
    author_email = "lhotka@nic.cz",
    url = "https://github.com/CZ-NIC/yangson",
    entry_points = {
        "console_scripts": ["yangson=yangson.__main__:main"]
        },
    install_requires = ["PyXB"],
    tests_require = ["pytest"],
    keywords = ["yang", "data model", "configuration", "json"],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Systems Administration"],
    long_description = """\
.. |date| date::

******************
Welcome to Yangson
******************

:Author: Ladislav Lhotka <lhotka@nic.cz>
:Date: |date|

*Yangson* is a Python 3 library for working with `JSON encoded`_
configuration and state data modelled using the YANG_
data modelling language.

Installation
============

::

    python -m pip install yangson

Note that *Yangson* requires Python 3.6 or higher.

Links
=====

* `Git repository`_
* `Documentation`_

.. _JSON encoded: https://tools.ietf.org/html/rfc7951
.. _YANG: https://tools.ietf.org/html/rfc7950
.. _Git repository: https://github.com/CZ-NIC/yangson
.. _Documentation: https://yangson.labs.nic.cz
"""
    )
