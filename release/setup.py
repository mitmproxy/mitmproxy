from setuptools import setup

setup(
    name='mitmproxy-rtool',
    version="1.0",
    py_modules=["rtool"],
    install_requires=[
        "click>=6.2, <7.0",
        "twine>=1.6.5, <1.9",
        "virtualenv>=14.0.5, <15.2",
        "wheel>=0.29.0, <0.30",
        "pysftp==0.2.8",
        "colorama>=0.3.7, < 0.4",
    ],
    entry_points={
        "console_scripts": [
            "rtool=rtool:cli",
        ],
    },
)
