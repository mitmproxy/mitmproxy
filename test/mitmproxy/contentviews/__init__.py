import sys

if sys.version_info < (3, 13):
    from typing_extensions import deprecated
else:
    from warnings import deprecated


@deprecated("Use `mitmproxy.contentviews.Contentview` instead.")
def full_eval(instance):
    def call(data, **metadata):
        x = instance(data, **metadata)
        if x is None:
            return None
        name, generator = x
        return name, list(generator)

    return call
