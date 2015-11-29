from setuptools import setup, find_packages

setup(
    name='mitmproxy-rtool',
    version='1.0',
    py_modules=['rtool'],
    install_requires=[
        'click>=6.2',
        'twine>=1.6.4',
        'virtualenv>=13.1.2',
        'wheel>=0.26.0',
    ],
    entry_points={
        'console_scripts': [
            'rtool=rtool:cli',
        ],
    },
)
