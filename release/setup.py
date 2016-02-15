from setuptools import setup

setup(
    name='mitmproxy-rtool',
    version="1.0",
    py_modules=["rtool"],
    install_requires=[
        "click>=6.2, <7.0",
        "twine>=1.6.5, <1.7",
        "virtualenv>=14.0.5, <14.1",
        "wheel>=0.29.0, <0.30",
        "six>=1.10.0, <1.11",
        "pysftp>=0.2.8, <0.3",
    ],
    entry_points={
        "console_scripts": [
            "rtool=rtool:cli",
        ],
    },
)
