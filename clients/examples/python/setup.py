#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages
from setuptools import setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = []

test_requirements = []

setup(
    author="Browserup Inc.",
    author_email="developers@browserup.com",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Browserup MitmProxy Python Client Usage Example",
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="browserup_mitmproxy_python_client_usage_example",
    name="browserup_mitmproxy_python_client_usage_example",
    packages=find_packages(
        include=[
            "browserup_mitmproxy_python_client_usage_example",
            "browserup_mitmproxy_python_client_usage_example.*",
        ]
    ),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/browserup/browserup_mitmproxy_python_client_usage_example",
    version="0.1.0",
    zip_safe=False,
)
