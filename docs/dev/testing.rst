.. _testing:

Testing
=======

All the mitmproxy projects strive to maintain 100% code coverage. In general,
patches and pull requests will be declined unless they're accompanied by a
suitable extension to the test suite.

Our tests are written for the `py.test`_ or nose_ test frameworks.
At the point where you send your pull request, a command like this:

>>> py.test --cov mitmproxy --cov netlib

Should give output something like this:

.. code-block:: none

    > ---------- coverage: platform darwin, python 2.7.2-final-0 --
    > Name                   Stmts   Miss  Cover   Missing
    > ----------------------------------------------------
    > mitmproxy/__init__         0      0   100%
    > mitmproxy/app              4      0   100%
    > mitmproxy/cmdline        100      0   100%
    > mitmproxy/controller      69      0   100%
    > mitmproxy/dump           150      0   100%
    > mitmproxy/encoding        39      0   100%
    > mitmproxy/flowfilter     201      0   100%
    > mitmproxy/flow           891      0   100%
    > mitmproxy/proxy          427      0   100%
    > mitmproxy/script          27      0   100%
    > mitmproxy/utils          133      0   100%
    > mitmproxy/version          4      0   100%
    > ----------------------------------------------------
    > TOTAL                   2045      0   100%
    > ----------------------------------------------------
    > Ran 251 tests in 11.864s


There are exceptions to the coverage requirement - for instance, much of the
console interface code can't sensibly be unit tested. These portions are
excluded from coverage analysis either in the **.coveragerc** file, or using
**#pragma no-cover** directives. To keep our coverage analysis relevant, we use
these measures as sparingly as possible.

.. _nose: https://nose.readthedocs.org/en/latest/
.. _py.test: https://pytest.org/
