from distutils.core import setup

setup(
    name = "yangson",
    packages = ["yangson"],
    version = "1.0.0",
    description = "Library for working with data modelled in YANG",
    author = "Ladislav Lhotka",
    author_email = "lhotka@nic.cz",
    url = "https://gitlab.labs.nic.cz/llhotka/yangson",
    install_requires = ['PyXB'],
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

=======
Yangson
=======
:Author: Ladislav Lhotka <lhotka@nic.cz>
:Date: |date|

Python library for working with YANG_ data models and JSON-encoded
data.

.. _YANG: https://tools.ietf.org/html/draft-ietf-netmod-rfc6020bis
"""
    )
