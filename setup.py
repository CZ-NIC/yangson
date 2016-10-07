from distutils.core import setup

def contents(*filenames):
    buf = []
    for filename in filenames:
        with open(filename, encoding="utf-8") as fp:
            buf.append(fp.read())
    return "\n\n".join(buf)

setup(
    name = "yangson",
    packages = ["yangson"],
    version = "1.0.0",
    description = "Library for working with data modelled in YANG",
    author = "Ladislav Lhotka",
    author_email = "lhotka@nic.cz",
    url = "https://github.com/CZ-NIC/yangson",
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
    long_description = contents("README.rst")
    )
