#!/usr/bin/python
#
# Urwid raw display module
#    Copyright (C) 2004-2009  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/

from __future__ import division, print_function

"""
Direct terminal UI implementation
"""

import os
import select
import struct
import sys
import signal
import socket
import threading


if os.name == "nt":
    IS_WINDOWS = True
    from . import win32
    from ctypes import byref
else:
    IS_WINDOWS = False
    import fcntl
    import termios
    import tty

from urwid import util
from urwid import escape
from urwid.display_common import BaseScreen, RealTerminal, \
    UPDATE_PALETTE_ENTRY, AttrSpec, UNPRINTABLE_TRANS_TABLE, \
    INPUT_DESCRIPTORS_CHANGED
from urwid import signals
from urwid.compat import PYTHON3, bytes, B

from subprocess import Popen, PIPE

STDIN = object()


class Screen(BaseScreen, RealTerminal):
    def __init__(self, input=STDIN, output=sys.stdout):
        """Initialize a screen that directly prints escape codes to an output
        terminal.
        """
        super(Screen, self).__init__()
        self._pal_escape = {}
        self._pal_attrspec = {}
        signals.connect_signal(self, UPDATE_PALETTE_ENTRY,
            self._on_update_palette_entry)
        self.colors = 16 # FIXME: detect this
        self.has_underline = True # FIXME: detect this
        self._keyqueue = []
        self.prev_input_resize = 0
        self.set_input_timeouts()
        self.screen_buf = None
        self._screen_buf_canvas = None
        self._resized = False
        self.maxrow = None
        self.gpm_mev = None
        self.gpm_event_pending = False
        self._mouse_tracking_enabled = False
        self.last_bstate = 0
        self._setup_G1_done = False
        self._rows_used = None
        self._cy = 0
        self.term = os.environ.get('TERM', '')
        self.fg_bright_is_bold = not self.term.startswith("xterm")
        self.bg_bright_is_blink = (self.term == "linux")
        self.back_color_erase = not self.term.startswith("screen")
        self.register_palette_entry( None, 'default','default')
        self._next_timeout = None
        self.signal_handler_setter = signal.signal

        # Our connections to the world
        self._term_output_file = output
        if input is STDIN:
            if IS_WINDOWS:
                input, self._send_input = socket.socketpair()
            else:
                input = sys.stdin
        self._term_input_file = input

        # pipe for signalling external event loops about resize events
        self._resize_pipe_rd, self._resize_pipe_wr = socket.socketpair()
        self._resize_pipe_rd.setblocking(False)

    def _input_fileno(self):
        """Returns the fileno of the input stream, or None if it doesn't have one.  A stream without a fileno can't participate in whatever.
        """
        if hasattr(self._term_input_file, 'fileno'):
            return self._term_input_file.fileno()
        else:
            return None

    def _on_update_palette_entry(self, name, *attrspecs):
        # copy the attribute to a dictionary containing the escape seqences
        a = attrspecs[{16:0,1:1,88:2,256:3,2**24:4}[self.colors]]
        self._pal_attrspec[name] = a
        self._pal_escape[name] = self._attrspec_to_escape(a)

    def set_input_timeouts(self, max_wait=None, complete_wait=0.125,
        resize_wait=0.125):
        """
        Set the get_input timeout values.  All values are in floating
        point numbers of seconds.

        max_wait -- amount of time in seconds to wait for input when
            there is no input pending, wait forever if None
        complete_wait -- amount of time in seconds to wait when
            get_input detects an incomplete escape sequence at the
            end of the available input
        resize_wait -- amount of time in seconds to wait for more input
            after receiving two screen resize requests in a row to
            stop Urwid from consuming 100% cpu during a gradual
            window resize operation
        """
        self.max_wait = max_wait
        if max_wait is not None:
            if self._next_timeout is None:
                self._next_timeout = max_wait
            else:
                self._next_timeout = min(self._next_timeout, self.max_wait)
        self.complete_wait = complete_wait
        self.resize_wait = resize_wait

    def _sigwinch_handler(self, signum, frame=None):
        """
        frame -- will always be None when the GLib event loop is being used.
        """
        if not self._resized:
            self._resize_pipe_wr.send(B("R"))
        self._resized = True
        self.screen_buf = None

    def _sigcont_handler(self, signum, frame=None):
        """
        frame -- will always be None when the GLib event loop is being used.
        """

        self.stop()
        self.start()
        self._sigwinch_handler(None, None)

    def signal_init(self):
        """
        Called in the startup of run wrapper to set the SIGWINCH
        and SIGCONT signal handlers.

        Override this function to call from main thread in threaded
        applications.
        """
        self.signal_handler_setter(signal.SIGWINCH, self._sigwinch_handler)
        self.signal_handler_setter(signal.SIGCONT, self._sigcont_handler)

    def signal_restore(self):
        """
        Called in the finally block of run wrapper to restore the
        SIGWINCH and SIGCONT signal handlers.

        Override this function to call from main thread in threaded
        applications.
        """
        self.signal_handler_setter(signal.SIGCONT, signal.SIG_DFL)
        self.signal_handler_setter(signal.SIGWINCH, signal.SIG_DFL)

    def set_mouse_tracking(self, enable=True):
        """
        Enable (or disable) mouse tracking.

        After calling this function get_input will include mouse
        click events along with keystrokes.
        """
        enable = bool(enable)
        if enable == self._mouse_tracking_enabled:
            return

        self._mouse_tracking(enable)
        self._mouse_tracking_enabled = enable

    def _mouse_tracking(self, enable):
        if enable:
            self.write(escape.MOUSE_TRACKING_ON)
            self._start_gpm_tracking()
        else:
            self.write(escape.MOUSE_TRACKING_OFF)
            self._stop_gpm_tracking()

    def _start_gpm_tracking(self):
        if not os.path.isfile("/usr/bin/mev"):
            return
        if not os.environ.get('TERM',"").lower().startswith("linux"):
            return
        if not Popen:
            return
        m = Popen(["/usr/bin/mev","-e","158"], stdin=PIPE, stdout=PIPE,
            close_fds=True)
        fcntl.fcntl(m.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
        self.gpm_mev = m

    def _stop_gpm_tracking(self):
        if not self.gpm_mev:
            return
        os.kill(self.gpm_mev.pid, signal.SIGINT)
        os.waitpid(self.gpm_mev.pid, 0)
        self.gpm_mev = None

    _dwOriginalOutMode = None
    _dwOriginalInMode = None

    def _start(self, alternate_buffer=True):
        """
        Initialize the screen and input mode.

        alternate_buffer -- use alternate screen buffer
        """
        if alternate_buffer:
            self.write(escape.SWITCH_TO_ALTERNATE_BUFFER)
            self._rows_used = None
        else:
            self._rows_used = 0

        fd = self._input_fileno()
        if fd is not None and os.isatty(fd) and not IS_WINDOWS:
            self._old_termios_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)

        if IS_WINDOWS:
            hOut = win32.GetStdHandle(win32.STD_OUTPUT_HANDLE)
            hIn = win32.GetStdHandle(win32.STD_INPUT_HANDLE)
            self._dwOriginalOutMode = win32.DWORD()
            self._dwOriginalInMode = win32.DWORD()
            win32.GetConsoleMode(hOut, byref(self._dwOriginalOutMode))
            win32.GetConsoleMode(hIn, byref(self._dwOriginalInMode))
            # TODO: Restore on exit

            dwOutMode = win32.DWORD(
                self._dwOriginalOutMode.value | win32.ENABLE_VIRTUAL_TERMINAL_PROCESSING | win32.DISABLE_NEWLINE_AUTO_RETURN)
            dwInMode = win32.DWORD(
                self._dwOriginalInMode.value | win32.ENABLE_WINDOW_INPUT | win32.ENABLE_VIRTUAL_TERMINAL_INPUT
            )

            ok = win32.SetConsoleMode(hOut, dwOutMode)
            assert ok
            ok = win32.SetConsoleMode(hIn, dwInMode)
            assert ok
        else:
            self.signal_init()
        self._alternate_buffer = alternate_buffer
        self._next_timeout = self.max_wait

        if not self._signal_keys_set and not IS_WINDOWS:
            self._old_signal_keys = self.tty_signal_keys(fileno=fd)

        signals.emit_signal(self, INPUT_DESCRIPTORS_CHANGED)
        # restore mouse tracking to previous state
        self._mouse_tracking(self._mouse_tracking_enabled)

        return super(Screen, self)._start()

    def _stop(self):
        """
        Restore the screen.
        """
        self.clear()

        signals.emit_signal(self, INPUT_DESCRIPTORS_CHANGED)

        if not IS_WINDOWS:
            self.signal_restore()

        fd = self._input_fileno()
        if fd is not None and os.isatty(fd) and not IS_WINDOWS:
            termios.tcsetattr(fd, termios.TCSADRAIN, self._old_termios_settings)

        self._mouse_tracking(False)

        move_cursor = ""
        if self._alternate_buffer:
            move_cursor = escape.RESTORE_NORMAL_BUFFER
        elif self.maxrow is not None:
            move_cursor = escape.set_cursor_position(
                0, self.maxrow)
        self.write(
            self._attrspec_to_escape(AttrSpec('',''))
            + escape.SI
            + move_cursor
            + escape.SHOW_CURSOR)
        self.flush()

        if self._old_signal_keys:
            self.tty_signal_keys(*(self._old_signal_keys + (fd,)))

        if IS_WINDOWS:
            hOut = win32.GetStdHandle(win32.STD_OUTPUT_HANDLE)
            hIn = win32.GetStdHandle(win32.STD_INPUT_HANDLE)
            ok = win32.SetConsoleMode(hOut, self._dwOriginalOutMode)
            assert ok
            ok = win32.SetConsoleMode(hIn, self._dwOriginalInMode)
            assert ok

        super(Screen, self)._stop()


    def write(self, data):
        """Write some data to the terminal.

        You may wish to override this if you're using something other than
        regular files for input and output.
        """
        self._term_output_file.write(data)

    def flush(self):
        """Flush the output buffer.

        You may wish to override this if you're using something other than
        regular files for input and output.
        """
        self._term_output_file.flush()

    def get_input(self, raw_keys=False):
        """Return pending input as a list.

        raw_keys -- return raw keycodes as well as translated versions

        This function will immediately return all the input since the
        last time it was called.  If there is no input pending it will
        wait before returning an empty list.  The wait time may be
        configured with the set_input_timeouts function.

        If raw_keys is False (default) this function will return a list
        of keys pressed.  If raw_keys is True this function will return
        a ( keys pressed, raw keycodes ) tuple instead.

        Examples of keys returned:

        * ASCII printable characters:  " ", "a", "0", "A", "-", "/"
        * ASCII control characters:  "tab", "enter"
        * Escape sequences:  "up", "page up", "home", "insert", "f1"
        * Key combinations:  "shift f1", "meta a", "ctrl b"
        * Window events:  "window resize"

        When a narrow encoding is not enabled:

        * "Extended ASCII" characters:  "\\xa1", "\\xb2", "\\xfe"

        When a wide encoding is enabled:

        * Double-byte characters:  "\\xa1\\xea", "\\xb2\\xd4"

        When utf8 encoding is enabled:

        * Unicode characters: u"\\u00a5", u'\\u253c"

        Examples of mouse events returned:

        * Mouse button press: ('mouse press', 1, 15, 13),
                              ('meta mouse press', 2, 17, 23)
        * Mouse drag: ('mouse drag', 1, 16, 13),
                      ('mouse drag', 1, 17, 13),
                      ('ctrl mouse drag', 1, 18, 13)
        * Mouse button release: ('mouse release', 0, 18, 13),
                                ('ctrl mouse release', 0, 17, 23)
        """
        assert self._started

        self._wait_for_input_ready(self._next_timeout)
        keys, raw = self.parse_input(None, None, self.get_available_raw_input())

        # Avoid pegging CPU at 100% when slowly resizing
        if keys==['window resize'] and self.prev_input_resize:
            while True:
                self._wait_for_input_ready(self.resize_wait)
                keys, raw2 = self.parse_input(None, None, self.get_available_raw_input())
                raw += raw2
                #if not keys:
                #    keys, raw2 = self._get_input(
                #        self.resize_wait)
                #    raw += raw2
                if keys!=['window resize']:
                    break
            if keys[-1:]!=['window resize']:
                keys.append('window resize')

        if keys==['window resize']:
            self.prev_input_resize = 2
        elif self.prev_input_resize == 2 and not keys:
            self.prev_input_resize = 1
        else:
            self.prev_input_resize = 0

        if raw_keys:
            return keys, raw
        return keys

    def get_input_descriptors(self):
        """
        Return a list of integer file descriptors that should be
        polled in external event loops to check for user input.

        Use this method if you are implementing your own event loop.

        This method is only called by `hook_event_loop`, so if you override
        that, you can safely ignore this.
        """
        if not self._started:
            return []

        fd_list = [self._resize_pipe_rd]
        fd = self._input_fileno()
        if fd is not None:
            fd_list.append(fd)
        if self.gpm_mev is not None:
            fd_list.append(self.gpm_mev.stdout.fileno())
        return fd_list

    _current_event_loop_handles = ()

    def unhook_event_loop(self, event_loop):
        """
        Remove any hooks added by hook_event_loop.
        """
        if self._input_thread is not None:
            self._input_thread.should_exit = True
            self._input_thread = None

        for handle in self._current_event_loop_handles:
            event_loop.remove_watch_file(handle)

        if self._input_timeout:
            event_loop.remove_alarm(self._input_timeout)
            self._input_timeout = None

    def hook_event_loop(self, event_loop, callback):
        """
        Register the given callback with the event loop, to be called with new
        input whenever it's available.  The callback should be passed a list of
        processed keys and a list of unprocessed keycodes.

        Subclasses may wish to use parse_input to wrap the callback.
        """
        if IS_WINDOWS:
            self._input_thread = ReadInputThread(self._send_input, lambda: self._sigwinch_handler(0))
            self._input_thread.start()
        if hasattr(self, 'get_input_nonblocking'):
            wrapper = self._make_legacy_input_wrapper(event_loop, callback)
        else:
            wrapper = lambda: self.parse_input(
                event_loop, callback, self.get_available_raw_input())
        fds = self.get_input_descriptors()
        handles = [event_loop.watch_file(fd, wrapper) for fd in fds]
        self._current_event_loop_handles = handles

    _input_thread = None
    _input_timeout = None
    _partial_codes = None

    def _make_legacy_input_wrapper(self, event_loop, callback):
        """
        Support old Screen classes that still have a get_input_nonblocking and
        expect it to work.
        """
        def wrapper():
            if self._input_timeout:
                event_loop.remove_alarm(self._input_timeout)
                self._input_timeout = None
            timeout, keys, raw = self.get_input_nonblocking()
            if timeout is not None:
                self._input_timeout = event_loop.alarm(timeout, wrapper)

            callback(keys, raw)

        return wrapper

    def get_available_raw_input(self):
        """
        Return any currently-available input.  Does not block.

        This method is only used by the default `hook_event_loop`
        implementation; you can safely ignore it if you implement your own.
        """
        codes = self._get_gpm_codes() + self._get_keyboard_codes()

        if self._partial_codes:
            codes = self._partial_codes + codes
            self._partial_codes = None

        # clean out the pipe used to signal external event loops
        # that a resize has occurred
        try:
            while True: self._resize_pipe_rd.recv(1)
        except OSError:
            pass

        return codes

    def parse_input(self, event_loop, callback, codes, wait_for_more=True):
        """
        Read any available input from get_available_raw_input, parses it into
        keys, and calls the given callback.

        The current implementation tries to avoid any assumptions about what
        the screen or event loop look like; it only deals with parsing keycodes
        and setting a timeout when an incomplete one is detected.

        `codes` should be a sequence of keycodes, i.e. bytes.  A bytearray is
        appropriate, but beware of using bytes, which only iterates as integers
        on Python 3.
        """
        # Note: event_loop may be None for 100% synchronous support, only used
        # by get_input.  Not documented because you shouldn't be doing it.
        if self._input_timeout and event_loop:
            event_loop.remove_alarm(self._input_timeout)
            self._input_timeout = None

        original_codes = codes
        processed = []
        try:
            while codes:
                run, codes = escape.process_keyqueue(
                    codes, wait_for_more)
                processed.extend(run)
        except escape.MoreInputRequired:
            # Set a timer to wait for the rest of the input; if it goes off
            # without any new input having come in, use the partial input
            k = len(original_codes) - len(codes)
            processed_codes = original_codes[:k]
            self._partial_codes = codes

            def _parse_incomplete_input():
                self._input_timeout = None
                self._partial_codes = None
                self.parse_input(
                    event_loop, callback, codes, wait_for_more=False)
            if event_loop:
                self._input_timeout = event_loop.alarm(
                    self.complete_wait, _parse_incomplete_input)

        else:
            processed_codes = original_codes
            self._partial_codes = None

        if self._resized:
            processed.append('window resize')
            self._resized = False

        if callback:
            callback(processed, processed_codes)
        else:
            # For get_input
            return processed, processed_codes

    def _get_keyboard_codes(self):
        codes = []
        while True:
            code = self._getch_nodelay()
            if code < 0:
                break
            codes.append(code)
        return codes

    def _get_gpm_codes(self):
        codes = []
        try:
            while self.gpm_mev is not None and self.gpm_event_pending:
                codes.extend(self._encode_gpm_event())
        except IOError as e:
            if e.args[0] != 11:
                raise
        return codes

    def _wait_for_input_ready(self, timeout):
        ready = None
        fd_list = []
        fd = self._input_fileno()
        if fd is not None:
            fd_list.append(fd)
        if self.gpm_mev is not None:
            fd_list.append(self.gpm_mev.stdout.fileno())
        while True:
            try:
                if timeout is None:
                    ready,w,err = select.select(
                        fd_list, [], fd_list)
                else:
                    ready,w,err = select.select(
                        fd_list,[],fd_list, timeout)
                break
            except select.error as e:
                if e.args[0] != 4:
                    raise
                if self._resized:
                    ready = []
                    break
        return ready

    def _getch(self, timeout):
        ready = self._wait_for_input_ready(timeout)
        if self.gpm_mev is not None:
            if self.gpm_mev.stdout.fileno() in ready:
                self.gpm_event_pending = True
        fd = self._input_fileno()
        if fd is not None and fd in ready:
            if IS_WINDOWS:
                return ord(self._term_input_file.recv(1))
            else:
                return ord(os.read(fd, 1))
        return -1

    def _encode_gpm_event( self ):
        self.gpm_event_pending = False
        s = self.gpm_mev.stdout.readline().decode('ascii')
        l = s.split(",")
        if len(l) != 6:
            # unexpected output, stop tracking
            self._stop_gpm_tracking()
            signals.emit_signal(self, INPUT_DESCRIPTORS_CHANGED)
            return []
        ev, x, y, ign, b, m = s.split(",")
        ev = int( ev.split("x")[-1], 16)
        x = int( x.split(" ")[-1] )
        y = int( y.lstrip().split(" ")[0] )
        b = int( b.split(" ")[-1] )
        m = int( m.split("x")[-1].rstrip(), 16 )

        # convert to xterm-like escape sequence

        last = next = self.last_bstate
        l = []

        mod = 0
        if m & 1:    mod |= 4 # shift
        if m & 10:    mod |= 8 # alt
        if m & 4:    mod |= 16 # ctrl

        def append_button( b ):
            b |= mod
            l.extend([ 27, ord('['), ord('M'), b+32, x+32, y+32 ])

        def determine_button_release( flag ):
            if b & 4 and last & 1:
                append_button( 0 + flag )
                next |= 1
            if b & 2 and last & 2:
                append_button( 1 + flag )
                next |= 2
            if b & 1 and last & 4:
                append_button( 2 + flag )
                next |= 4

        if ev == 20 or ev == 36 or ev == 52: # press
            if b & 4 and last & 1 == 0:
                append_button( 0 )
                next |= 1
            if b & 2 and last & 2 == 0:
                append_button( 1 )
                next |= 2
            if b & 1 and last & 4 == 0:
                append_button( 2 )
                next |= 4
        elif ev == 146: # drag
            if b & 4:
                append_button( 0 + escape.MOUSE_DRAG_FLAG )
            elif b & 2:
                append_button( 1 + escape.MOUSE_DRAG_FLAG )
            elif b & 1:
                append_button( 2 + escape.MOUSE_DRAG_FLAG )
        else: # release
            if b & 4 and last & 1:
                append_button( 0 + escape.MOUSE_RELEASE_FLAG )
                next &= ~ 1
            if b & 2 and last & 2:
                append_button( 1 + escape.MOUSE_RELEASE_FLAG )
                next &= ~ 2
            if b & 1 and last & 4:
                append_button( 2 + escape.MOUSE_RELEASE_FLAG )
                next &= ~ 4
        if ev == 40: # double click (release)
            if b & 4 and last & 1:
                append_button( 0 + escape.MOUSE_MULTIPLE_CLICK_FLAG )
            if b & 2 and last & 2:
                append_button( 1 + escape.MOUSE_MULTIPLE_CLICK_FLAG )
            if b & 1 and last & 4:
                append_button( 2 + escape.MOUSE_MULTIPLE_CLICK_FLAG )
        elif ev == 52:
            if b & 4 and last & 1:
                append_button( 0 + escape.MOUSE_MULTIPLE_CLICK_FLAG*2 )
            if b & 2 and last & 2:
                append_button( 1 + escape.MOUSE_MULTIPLE_CLICK_FLAG*2 )
            if b & 1 and last & 4:
                append_button( 2 + escape.MOUSE_MULTIPLE_CLICK_FLAG*2 )

        self.last_bstate = next
        return l

    def _getch_nodelay(self):
        return self._getch(0)


    def get_cols_rows(self):
        """Return the terminal dimensions (num columns, num rows)."""
        y, x = 24, 80
        try:
            if hasattr(self._term_output_file, 'fileno'):
                if IS_WINDOWS:
                    assert self._term_output_file == sys.stdout
                    handle = win32.GetStdHandle(win32.STD_OUTPUT_HANDLE)
                    info = win32.CONSOLE_SCREEN_BUFFER_INFO()
                    ok = win32.GetConsoleScreenBufferInfo(handle, byref(info))
                    if ok == 0:
                        raise IOError()
                    y, x = info.dwSize.Y, info.dwSize.X
                else:
                    buf = fcntl.ioctl(self._term_output_file.fileno(),
                                    termios.TIOCGWINSZ, ' '*4)
                    y, x = struct.unpack('hh', buf)
        except IOError:
            # Term size could not be determined
            pass
        self.maxrow = y
        return x, y

    def _setup_G1(self):
        """
        Initialize the G1 character set to graphics mode if required.
        """
        if self._setup_G1_done:
            return

        while True:
            try:
                self.write(escape.DESIGNATE_G1_SPECIAL)
                self.flush()
                break
            except IOError:
                pass
        self._setup_G1_done = True


    def draw_screen(self, maxres, r ):
        """Paint screen with rendered canvas."""

        (maxcol, maxrow) = maxres

        assert self._started

        assert maxrow == r.rows()

        # quick return if nothing has changed
        if self.screen_buf and r is self._screen_buf_canvas:
            return

        self._setup_G1()

        if self._resized:
            # handle resize before trying to draw screen
            return

        o = [escape.HIDE_CURSOR, self._attrspec_to_escape(AttrSpec('',''))]

        def partial_display():
            # returns True if the screen is in partial display mode
            # ie. only some rows belong to the display
            return self._rows_used is not None

        if not partial_display():
            o.append(escape.CURSOR_HOME)

        if self.screen_buf:
            osb = self.screen_buf
        else:
            osb = []
        sb = []
        cy = self._cy
        y = -1

        def set_cursor_home():
            if not partial_display():
                return escape.set_cursor_position(0, 0)
            return (escape.CURSOR_HOME_COL +
                escape.move_cursor_up(cy))

        def set_cursor_row(y):
            if not partial_display():
                return escape.set_cursor_position(0, y)
            return escape.move_cursor_down(y - cy)

        def set_cursor_position(x, y):
            if not partial_display():
                return escape.set_cursor_position(x, y)
            if cy > y:
                return ('\b' + escape.CURSOR_HOME_COL +
                    escape.move_cursor_up(cy - y) +
                    escape.move_cursor_right(x))
            return ('\b' + escape.CURSOR_HOME_COL +
                escape.move_cursor_down(y - cy) +
                escape.move_cursor_right(x))

        def is_blank_row(row):
            if len(row) > 1:
                return False
            if row[0][2].strip():
                return False
            return True

        def attr_to_escape(a):
            if a in self._pal_escape:
                return self._pal_escape[a]
            elif isinstance(a, AttrSpec):
                return self._attrspec_to_escape(a)
            # undefined attributes use default/default
            # TODO: track and report these
            return self._attrspec_to_escape(
                AttrSpec('default','default'))

        def using_standout_or_underline(a):
            a = self._pal_attrspec.get(a, a)
            return isinstance(a, AttrSpec) and (a.standout or a.underline)

        ins = None
        o.append(set_cursor_home())
        cy = 0
        for row in r.content():
            y += 1
            if osb and y < len(osb) and osb[y] == row:
                # this row of the screen buffer matches what is
                # currently displayed, so we can skip this line
                sb.append( osb[y] )
                continue

            sb.append(row)

            # leave blank lines off display when we are using
            # the default screen buffer (allows partial screen)
            if partial_display() and y > self._rows_used:
                if is_blank_row(row):
                    continue
                self._rows_used = y

            if y or partial_display():
                o.append(set_cursor_position(0, y))
            # after updating the line we will be just over the
            # edge, but terminals still treat this as being
            # on the same line
            cy = y

            whitespace_at_end = False
            if row:
                a, cs, run = row[-1]
                if (run[-1:] == B(' ') and self.back_color_erase
                        and not using_standout_or_underline(a)):
                    whitespace_at_end = True
                    row = row[:-1] + [(a, cs, run.rstrip(B(' ')))]
                elif y == maxrow-1 and maxcol > 1:
                    row, back, ins = self._last_row(row)

            first = True
            lasta = lastcs = None
            for (a,cs, run) in row:
                assert isinstance(run, bytes) # canvases should render with bytes
                if cs != 'U':
                    run = run.translate(UNPRINTABLE_TRANS_TABLE)
                if first or lasta != a:
                    o.append(attr_to_escape(a))
                    lasta = a
                if first or lastcs != cs:
                    assert cs in [None, "0", "U"], repr(cs)
                    if lastcs == "U":
                        o.append( escape.IBMPC_OFF )

                    if cs is None:
                        o.append( escape.SI )
                    elif cs == "U":
                        o.append( escape.IBMPC_ON )
                    else:
                        o.append( escape.SO )
                    lastcs = cs
                o.append( run )
                first = False
            if ins:
                (inserta, insertcs, inserttext) = ins
                ias = attr_to_escape(inserta)
                assert insertcs in [None, "0", "U"], repr(insertcs)
                if cs is None:
                    icss = escape.SI
                elif cs == "U":
                    icss = escape.IBMPC_ON
                else:
                    icss = escape.SO
                o += [    "\x08"*back,
                    ias, icss,
                    escape.INSERT_ON, inserttext,
                    escape.INSERT_OFF ]

                if cs == "U":
                    o.append(escape.IBMPC_OFF)
            if whitespace_at_end:
                o.append(escape.ERASE_IN_LINE_RIGHT)

        if r.cursor is not None:
            x,y = r.cursor
            o += [set_cursor_position(x, y),
                escape.SHOW_CURSOR  ]
            self._cy = y

        if self._resized:
            # handle resize before trying to draw screen
            return
        try:
            for l in o:
                if isinstance(l, bytes) and PYTHON3:
                    l = l.decode('utf-8', 'replace')
                self.write(l)
            self.flush()
        except IOError as e:
            # ignore interrupted syscall
            if e.args[0] != 4:
                raise

        self.screen_buf = sb
        self._screen_buf_canvas = r


    def _last_row(self, row):
        """On the last row we need to slide the bottom right character
        into place. Calculate the new line, attr and an insert sequence
        to do that.

        eg. last row:
        XXXXXXXXXXXXXXXXXXXXYZ

        Y will be drawn after Z, shifting Z into position.
        """

        new_row = row[:-1]
        z_attr, z_cs, last_text = row[-1]
        last_cols = util.calc_width(last_text, 0, len(last_text))
        last_offs, z_col = util.calc_text_pos(last_text, 0,
            len(last_text), last_cols-1)
        if last_offs == 0:
            z_text = last_text
            del new_row[-1]
            # we need another segment
            y_attr, y_cs, nlast_text = row[-2]
            nlast_cols = util.calc_width(nlast_text, 0,
                len(nlast_text))
            z_col += nlast_cols
            nlast_offs, y_col = util.calc_text_pos(nlast_text, 0,
                len(nlast_text), nlast_cols-1)
            y_text = nlast_text[nlast_offs:]
            if nlast_offs:
                new_row.append((y_attr, y_cs,
                    nlast_text[:nlast_offs]))
        else:
            z_text = last_text[last_offs:]
            y_attr, y_cs = z_attr, z_cs
            nlast_cols = util.calc_width(last_text, 0,
                last_offs)
            nlast_offs, y_col = util.calc_text_pos(last_text, 0,
                last_offs, nlast_cols-1)
            y_text = last_text[nlast_offs:last_offs]
            if nlast_offs:
                new_row.append((y_attr, y_cs,
                    last_text[:nlast_offs]))

        new_row.append((z_attr, z_cs, z_text))
        return new_row, z_col-y_col, (y_attr, y_cs, y_text)



    def clear(self):
        """
        Force the screen to be completely repainted on the next
        call to draw_screen().
        """
        self.screen_buf = None
        self.setup_G1 = True


    def _attrspec_to_escape(self, a):
        """
        Convert AttrSpec instance a to an escape sequence for the terminal

        >>> s = Screen()
        >>> s.set_terminal_properties(colors=256)
        >>> a2e = s._attrspec_to_escape
        >>> a2e(s.AttrSpec('brown', 'dark green'))
        '\\x1b[0;33;42m'
        >>> a2e(s.AttrSpec('#fea,underline', '#d0d'))
        '\\x1b[0;38;5;229;4;48;5;164m'
        """
        if self.term == 'fbterm':
            fg = escape.ESC + '[1;%d}' % (a.foreground_number,)
            bg = escape.ESC + '[2;%d}' % (a.background_number,)
            return fg + bg

        if a.foreground_true:
            fg = "38;2;%d;%d;%d" %(a.get_rgb_values()[0:3])
        elif a.foreground_high:
            fg = "38;5;%d" % a.foreground_number
        elif a.foreground_basic:
            if a.foreground_number > 7:
                if self.fg_bright_is_bold:
                    fg = "1;%d" % (a.foreground_number - 8 + 30)
                else:
                    fg = "%d" % (a.foreground_number - 8 + 90)
            else:
                fg = "%d" % (a.foreground_number + 30)
        else:
            fg = "39"
        st = ("1;" * a.bold + "3;" * a.italics +
              "4;" * a.underline + "5;" * a.blink +
              "7;" * a.standout + "9;" * a.strikethrough)
        if a.background_true:
             bg = "48;2;%d;%d;%d" %(a.get_rgb_values()[3:6])
        elif a.background_high:
            bg = "48;5;%d" % a.background_number
        elif a.background_basic:
            if a.background_number > 7:
                if self.bg_bright_is_blink:
                    bg = "5;%d" % (a.background_number - 8 + 40)
                else:
                    # this doesn't work on most terminals
                    bg = "%d" % (a.background_number - 8 + 100)
            else:
                bg = "%d" % (a.background_number + 40)
        else:
            bg = "49"
        return escape.ESC + "[0;%s;%s%sm" % (fg, st, bg)


    def set_terminal_properties(self, colors=None, bright_is_bold=None,
        has_underline=None):
        """
        colors -- number of colors terminal supports (1, 16, 88, 256, or 2**24)
            or None to leave unchanged
        bright_is_bold -- set to True if this terminal uses the bold
            setting to create bright colors (numbers 8-15), set to False
            if this Terminal can create bright colors without bold or
            None to leave unchanged
        has_underline -- set to True if this terminal can use the
            underline setting, False if it cannot or None to leave
            unchanged
        """
        if colors is None:
            colors = self.colors
        if bright_is_bold is None:
            bright_is_bold = self.fg_bright_is_bold
        if has_underline is None:
            has_underline = self.has_underline

        if colors == self.colors and bright_is_bold == self.fg_bright_is_bold \
            and has_underline == self.has_underline:
            return

        self.colors = colors
        self.fg_bright_is_bold = bright_is_bold
        self.has_underline = has_underline

        self.clear()
        self._pal_escape = {}
        for p,v in self._palette.items():
            self._on_update_palette_entry(p, *v)



    def reset_default_terminal_palette(self):
        """
        Attempt to set the terminal palette to default values as taken
        from xterm.  Uses number of colors from current
        set_terminal_properties() screen setting.
        """
        if self.colors == 1:
            return
        elif self.colors == 2**24:
            colors = 256
        else:
            colors = self.colors

        def rgb_values(n):
            if colors == 16:
                aspec = AttrSpec("h%d"%n, "", 256)
            else:
                aspec = AttrSpec("h%d"%n, "", colors)
            return aspec.get_rgb_values()[:3]

        entries = [(n,) + rgb_values(n) for n in range(min(colors, 256))]
        self.modify_terminal_palette(entries)


    def modify_terminal_palette(self, entries):
        """
        entries - list of (index, red, green, blue) tuples.

        Attempt to set part of the terminal palette (this does not work
        on all terminals.)  The changes are sent as a single escape
        sequence so they should all take effect at the same time.

        0 <= index < 256 (some terminals will only have 16 or 88 colors)
        0 <= red, green, blue < 256
        """

        if self.term == 'fbterm':
            modify = ["%d;%d;%d;%d" % (index, red, green, blue)
                for index, red, green, blue in entries]
            self.write("\x1b[3;"+";".join(modify)+"}")
        else:
            modify = ["%d;rgb:%02x/%02x/%02x" % (index, red, green, blue)
                for index, red, green, blue in entries]
            self.write("\x1b]4;"+";".join(modify)+"\x1b\\")
        self.flush()


    # shortcut for creating an AttrSpec with this screen object's
    # number of colors
    AttrSpec = lambda self, fg, bg: AttrSpec(fg, bg, self.colors)


class ReadInputThread(threading.Thread):
    name = "urwid Windows input reader"
    daemon = True
    should_exit: bool = False
    _input: socket.socket

    def __init__(self, input, resize):
        self._input = input
        self._resize = resize
        super().__init__()

    def run(self) -> None:
        hIn = win32.GetStdHandle(win32.STD_INPUT_HANDLE)
        MAX = 2048

        read = win32.DWORD(0)
        arrtype = win32.INPUT_RECORD * MAX
        input_records = arrtype()

        while True:
            win32.ReadConsoleInputW(hIn, byref(input_records), MAX, byref(read))
            if self.should_exit:
                return
            for i in range(read.value):
                inp = input_records[i]
                if inp.EventType == win32.EventType.KEY_EVENT:
                    if not inp.Event.KeyEvent.bKeyDown:
                        continue
                    self._input.send(inp.Event.KeyEvent.uChar.AsciiChar)
                elif inp.EventType == win32.EventType.WINDOW_BUFFER_SIZE_EVENT:
                    self._resize()
                else:
                    pass  # TODO: handle mouse events


def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()
