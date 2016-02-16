import sys

resolver = None

if sys.platform == "linux2":
    from . import linux
    resolver = linux.Resolver
elif sys.platform == "darwin":
    from . import osx
    resolver = osx.Resolver
elif sys.platform.startswith("freebsd"):
    from . import osx
    resolver = osx.Resolver
elif sys.platform == "win32":
    from . import windows
    resolver = windows.Resolver
