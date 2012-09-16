import sys

resolver = None
if sys.platform == "linux2":
    import linux
    resolver = linux.Resolver
elif sys.platform == "darwin":
    import osx
    resolver = osx.Resolver
