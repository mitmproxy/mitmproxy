.. _testing:

Testing
=======

All the mitmproxy projects strive to maintain 100% code coverage. In general,
patches and pull requests will be declined unless they're accompanied by a
suitable extension to the test suite.

Our tests are written for the `py.test`_ or nose_ test frameworks.
At the point where you send your pull request, a command like this:

>>> py.test -n 4 --cov libmproxy

Should give output something like this:

.. code-block:: none

    > ---------- coverage: platform darwin, python 2.7.2-final-0 --
    > Name                   Stmts   Miss  Cover   Missing
    > ----------------------------------------------------
    > libmproxy/__init__         0      0   100%
    > libmproxy/app              4      0   100%
    > libmproxy/cmdline        100      0   100%
    > libmproxy/controller      69      0   100%
    > libmproxy/dump           150      0   100%
    > libmproxy/encoding        39      0   100%
    > libmproxy/filt           201      0   100%
    > libmproxy/flow           891      0   100%
    > libmproxy/proxy          427      0   100%
    > libmproxy/script          27      0   100%
    > libmproxy/utils          133      0   100%
    > libmproxy/version          4      0   100%
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
