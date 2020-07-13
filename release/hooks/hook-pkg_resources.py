# flake8: noqa

# temporary fix for https://github.com/pypa/setuptools/issues/1963
# can be removed when we upgrade to PyInstaller 3.7.
hiddenimports = collect_submodules('pkg_resources._vendor')
hiddenimports.append('pkg_resources.py2_warn')
excludedimports = ['__main__']
