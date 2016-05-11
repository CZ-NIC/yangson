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
    version = "0.1.37",
    description = "Library for working with YANG schemas and data",
    author = "Ladislav Lhotka",
    author_email = "lhotka@nic.cz",
    url = "https://gitlab.labs.nic.cz/llhotka/yangson",
    tests_require = ["pytest"],
    keywords = ["yang", "data model", "configuration", "json"],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Topic :: Software Development :: Libraries" ],
    long_description = contents("README.rst")
    )
