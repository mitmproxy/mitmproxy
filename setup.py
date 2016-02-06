from setuptools import setup, find_packages

setup(
    name='mitmproxy-rtool',
    version='1.0',
    py_modules=['rtool'],
    install_requires=[
        "click>=6.2, <7.0",
        'twine>=1.6.5, <1.7',
        'virtualenv>=14.0.5, <14.1',
        'wheel>=0.26.0, <0.27',
    ],
    entry_points={
        'console_scripts': [
            'rtool=rtool:cli',
        ],
    },
)
