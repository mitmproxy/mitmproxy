import datetime
import libtmux
import random
import subprocess
import threading
import time


class CliDirector:
    def __init__(self):
        self.record_start = None
        self.pause_between_keys = 0.15
        self.pause_between_keys_rand = 0.2

    def start(self, filename: str, width: int = 0, height: int = 0) -> libtmux.Session:
        self.start_session()
        self.start_recording(filename, width, height)
        return self.tmux_session

    def start_session(self, width: int = 0, height: int = 0) -> libtmux.Session:
        self.tmux_server = libtmux.Server()
        self.tmux_session = self.tmux_server.new_session(session_name="asciinema_recorder", kill_session=True)
        self.tmux_pane = self.tmux_session.attached_window.attached_pane
        self.tmux_version = self.tmux_pane.display_message("#{version}", True)
        if width and height:
            self.resize_window(width, height)
        self.pause(3)
        return self.tmux_session

    def start_recording(self, filename: str) -> None:
        self.asciinema_proc = subprocess.Popen([
            "asciinema", "rec", "-y", "--overwrite", "-c", "tmux attach -t asciinema_recorder", filename])
        self.pause(1.5)
        self.record_start = datetime.datetime.now()

    def resize_window(self, width: int, height: int) -> None:
        subprocess.Popen(["resize", "-s", str(height), str(width)])

    def end(self) -> None:
        self.end_recording()
        self.end_session()

    def end_recording(self) -> None:
        self.asciinema_proc.terminate()
        self.asciinema_proc.wait(timeout=5)

    def end_session(self) -> None:
        self.tmux_session.kill_session()

    def press_key(self, keys: str, count=1) -> None:
        for i in range(count):
            self.tmux_pane.send_keys(cmd=keys, enter=False, suppress_history=False)
            self.pause(self.pause_between_keys + random.uniform(0, self.pause_between_keys_rand))

    def type(self, keys: str) -> None:
        for key in keys:
            self.press_key(key)

    def exec(self, keys: str) -> None:
        self.type(keys)
        self.pause(1.25)
        self.press_key("Enter")
        self.pause(0.5)

    def pause(self, seconds: float) -> None:
        time.sleep(seconds)

    def run_external(self, command: str) -> None:
        subprocess.run(command, shell=True)

    def message(self, msg: str, duration: int = 3) -> None:
        self.tmux_session.set_option("display-time", duration * 1000)
        self.tmux_pane.display_message(msg)
        self.pause(duration + 0.1)

    def popup(self, content: str, duration: int = 4) -> None:
        # todo: check if installed tmux version supports display-popup

        # tmux's display-popup is blocking, so we close it in a separate thread
        t=threading.Thread(target=self.close_popup, args=[duration])
        t.start()

        lines = content.splitlines()
        self.tmux_pane.cmd("display-popup", "", *lines)
        t.join()

    def close_popup(self, duration=0) -> None:
        self.pause(duration)
        self.tmux_pane.cmd("display-popup", "-C")

    @property
    def current_time(self) -> int:
        now = datetime.datetime.now()
        return (now - self.record_start).total_seconds()
