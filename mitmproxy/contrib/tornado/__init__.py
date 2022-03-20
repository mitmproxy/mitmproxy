"""
SPDX-License-Identifier: Apache-2.0

Vendored partial copy of https://github.com/tornadoweb/tornado/blob/master/tornado/platform/asyncio.py @ e18ea03
to fix https://github.com/tornadoweb/tornado/issues/3092. Can be removed once tornado >6.1 is out.
"""
import errno

import select
import tornado
import tornado.platform.asyncio


def patch_tornado():
    if tornado.version != "6.1":
        return

    def _run_select(self) -> None:
        while True:
            with self._select_cond:
                while self._select_args is None and not self._closing_selector:
                    self._select_cond.wait()
                if self._closing_selector:
                    return
                assert self._select_args is not None
                to_read, to_write = self._select_args
                self._select_args = None

            # We use the simpler interface of the select module instead of
            # the more stateful interface in the selectors module because
            # this class is only intended for use on windows, where
            # select.select is the only option. The selector interface
            # does not have well-documented thread-safety semantics that
            # we can rely on so ensuring proper synchronization would be
            # tricky.
            try:
                # On windows, selecting on a socket for write will not
                # return the socket when there is an error (but selecting
                # for reads works). Also select for errors when selecting
                # for writes, and merge the results.
                #
                # This pattern is also used in
                # https://github.com/python/cpython/blob/v3.8.0/Lib/selectors.py#L312-L317
                rs, ws, xs = select.select(to_read, to_write, to_write)
                ws = ws + xs
            except OSError as e:
                # After remove_reader or remove_writer is called, the file
                # descriptor may subsequently be closed on the event loop
                # thread. It's possible that this select thread hasn't
                # gotten into the select system call by the time that
                # happens in which case (at least on macOS), select may
                # raise a "bad file descriptor" error. If we get that
                # error, check and see if we're also being woken up by
                # polling the waker alone. If we are, just return to the
                # event loop and we'll get the updated set of file
                # descriptors on the next iteration. Otherwise, raise the
                # original error.
                if e.errno == getattr(errno, "WSAENOTSOCK", errno.EBADF):
                    rs, _, _ = select.select([self._waker_r.fileno()], [], [], 0)
                    if rs:
                        ws = []
                    else:
                        raise
                else:
                    raise

            try:
                self._real_loop.call_soon_threadsafe(self._handle_select, rs, ws)
            except RuntimeError:
                # "Event loop is closed". Swallow the exception for
                # consistency with PollIOLoop (and logical consistency
                # with the fact that we can't guarantee that an
                # add_callback that completes without error will
                # eventually execute).
                pass
            except AttributeError:
                # ProactorEventLoop may raise this instead of RuntimeError
                # if call_soon_threadsafe races with a call to close().
                # Swallow it too for consistency.
                pass

    tornado.platform.asyncio.AddThreadSelectorEventLoop._run_select = _run_select
