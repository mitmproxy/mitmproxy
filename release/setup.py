from setuptools import setup

setup(
    name='mitmproxy-rtool',
    version="1.0",
    py_modules=["rtool"],
    install_requires=[
        "click>=6.2, <7.0",
        "twine>=1.6.5, <1.10",
        "pysftp==0.2.8",
        "cryptography>=2.0.0, <2.1",
    ],
    entry_points={
        "console_scripts": [
            "rtool=rtool:cli",
        ],
    },
)
