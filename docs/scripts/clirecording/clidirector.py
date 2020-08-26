import datetime
import json
import libtmux
import random
import requests
import subprocess
import threading
import time
import typing


class CliDirector:
    def __init__(self):
        self.record_start = None
        self.pause_between_keys = 0.15
        self.pause_between_keys_rand = 0.2

    def start(self, filename: str, width: int = 0, height: int = 0) -> libtmux.Session:
        self.start_session(width, height)
        self.start_recording(filename)
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

    def press_key(self, keys: str, count=1, pause: typing.Optional[float] = None) -> None:
        if pause is None:
            pause = self.pause_between_keys
        for i in range(count):
            self.tmux_pane.send_keys(cmd=keys, enter=False, suppress_history=False)
            self.pause(pause + random.uniform(0, self.pause_between_keys_rand))

    def type(self, keys: str, pause: typing.Optional[float] = None) -> None:
        if pause is None:
            pause = self.pause_between_keys
        for key in keys:
            self.press_key(key, pause=pause)

    def exec(self, keys: str) -> None:
        self.type(keys)
        self.pause(1.25)
        self.press_key("Enter")
        self.pause(0.5)

    def pause(self, seconds: float) -> None:
        time.sleep(seconds)

    def run_external(self, command: str) -> None:
        subprocess.run(command, shell=True)

    def message(self, msg: str, duration: typing.Optional[int] = None, add_instruction: bool = True, instruction_html: str = "") -> None:
        if duration is None:
            duration = len(msg) * 0.075 # seconds
        self.tmux_session.set_option("display-time", int(duration * 1000)) # milliseconds
        self.tmux_pane.display_message(msg)

        # todo: this is a hack and needs refactoring (instruction() is only defined in MitmCliDirector)
        if add_instruction or instruction_html:
            if not instruction_html:
                instruction_html = msg
            self.instruction(title="", instruction=instruction_html, duration=duration)
        self.pause(duration)

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
    def current_time(self) -> float:
        now = datetime.datetime.now()
        return round((now - self.record_start).total_seconds(), 2)


# todo: title is not used at the moment
class InstructionSpec(typing.NamedTuple):
    title: str
    instruction: str
    time_from: float
    time_from_str: str
    time_to: float


class MitmCliDirector(CliDirector):
    def __init__(self):
        super().__init__()
        self.instructions: typing.List[InstructionSpec] = []

    def instruction(self, title: str, instruction: str, duration: float = 3, time_from: typing.Optional[float] = None, correction: float = 0) -> None:
        if time_from is None:
            time_from = self.current_time
        time_from_str = str(datetime.timedelta(seconds = int(time_from + correction)))[2:]

        self.instructions.append(InstructionSpec(
            str(len(self.instructions)+1) + ". " + title,
            str(len(self.instructions)+1) + ". " + instruction,
            time_from=time_from + correction,
            time_from_str=time_from_str,
            time_to=time_from - correction + duration
        ))

    def save_instructions(self, output_path: str) -> None:
        instr_as_dicts = []
        for instr in self.instructions:
            instr_as_dicts.append(instr._asdict())
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(instr_as_dicts, f, ensure_ascii=False, indent=4)

    def request(self, url: str, threaded: bool = False) -> None:
        if threaded:
            threading.Thread(target=lambda: requests.get(url, verify=False)).start()
        else:
            requests.get(url, verify=False)

    def init_flow_list(self, step: str) -> None:
        self.request(f"http://tutorial.mitm.it/mitmproxy/{step}")
        self.request("http://tutorial.mitm.it/static/asciinema-player.css")
        self.request("http://tutorial.mitm.it/static/bootstrap.min.css")
        self.request("http://tutorial.mitm.it/static/tutorial.css")
        self.request("http://tutorial.mitm.it/static/tutorial.js")
        self.request("http://tutorial.mitm.it/static/asciinema-player.js")
        self.request("http://tutorial.mitm.it/static/images/mitmproxy-long.png")
        self.request("http://tutorial.mitm.it/static/images/cat.jpg")
        self.request("http://tutorial.mitm.it/static/images/dog.jpg")
        self.request("http://tutorial.mitm.it/static/images/favicon.ico")
        self.request("http://tutorial.mitm.it/votes")
        self.pause(0.5)

    def end_recording(self) -> None:
        self.instructions = []
        super().end_recording()
