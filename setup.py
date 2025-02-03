#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

requirements = [
    "electrum_ecc",
    "websockets",
    "cryptography>=2.8",
    "aiorpcx>=0.22.0,<0.25",  # for taskgroup. remove when we use python 3.11
]

extras_require = {
    'tests': [
        'pytest-cov',
        'Click',
    ],
}

setup(
    author="The Electrum Developers",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    description="asyncio nostr client",
    entry_points={
        "console_scripts": [
            "aionostr=aionostr.cli:main",
        ],
    },
    install_requires=requirements,
    extras_require=extras_require,
    license="BSD license",
    long_description=readme,
    include_package_data=True,
    keywords="aionostr",
    name="electrum-aionostr",
    packages=['electrum_aionostr'],
    package_dir={'electrum_aionostr': 'aionostr'},
    url="https://github.com/spesmilo/electrum-aionostr",
    version="0.0.6",
    zip_safe=False,
)
