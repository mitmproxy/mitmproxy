import json
import libtmux
import random
import subprocess
import threading
import time
import typing


class InstructionSpec(typing.NamedTuple):
    instruction: str
    time_from: float
    time_to: float


class CliDirector:
    def __init__(self):
        self.record_start = None
        self.pause_between_keys = 0.2
        self.instructions: typing.List[InstructionSpec] = []

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
        self.record_start = time.time()

    def resize_window(self, width: int, height: int) -> None:
        subprocess.Popen(["resize", "-s", str(height), str(width)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def end(self) -> None:
        self.end_recording()
        self.end_session()

    def end_recording(self) -> None:
        self.asciinema_proc.terminate()
        self.asciinema_proc.wait(timeout=5)
        self.record_start = None
        self.instructions = []

    def end_session(self) -> None:
        self.tmux_session.kill_session()

    def press_key(self, keys: str, count=1, pause: typing.Optional[float] = None, target = None) -> None:
        if pause is None:
            pause = self.pause_between_keys
        if target is None:
            target = self.tmux_pane
        for i in range(count):
            if keys == " ":
                keys = "Space"
            target.send_keys(cmd=keys, enter=False, suppress_history=False)

            # inspired by https://github.com/dmotz/TuringType
            real_pause = random.uniform(0, pause) + 0.4 * pause
            if keys == "Space":
                real_pause += 1.5 * pause
            elif keys == ".":
                real_pause += pause
            elif random.random() > 0.75:
                real_pause += pause
            elif random.random() > 0.95:
                real_pause += 2 * pause
            self.pause(real_pause)

    def type(self, keys: str, pause: typing.Optional[float] = None, target = None) -> None:
        if pause is None:
            pause = self.pause_between_keys
        if target is None:
            target = self.tmux_pane
        target.select_pane()
        for key in keys:
            self.press_key(key, pause=pause, target=target)

    def exec(self, keys: str, target = None) -> None:
        if target is None:
            target = self.tmux_pane
        self.type(keys, target=target)
        self.pause(1.25)
        self.press_key("Enter", target=target)
        self.pause(0.5)

    def focus_pane(self, pane: libtmux.Pane, set_active_pane: bool = True) -> None:
        pane.select_pane()
        if set_active_pane:
            self.tmux_pane = pane

    def pause(self, seconds: float) -> None:
        time.sleep(seconds)

    def run_external(self, command: str) -> None:
        subprocess.run(command, shell=True)

    def message(self, msg: str, duration: typing.Optional[int] = None, add_instruction: bool = True, instruction_html: str = "") -> None:
        if duration is None:
            duration = len(msg) * 0.08  # seconds
        self.tmux_session.set_option("display-time", int(duration * 1000))  # milliseconds
        self.tmux_pane.display_message(" " + msg)

        if add_instruction or instruction_html:
            if not instruction_html:
                instruction_html = msg
            self.instruction(instruction=instruction_html, duration=duration)
        self.pause(duration + 0.5)

    def popup(self, content: str, duration: int = 4) -> None:
        # todo: check if installed tmux version supports display-popup

        # tmux's display-popup is blocking, so we close it in a separate thread
        t = threading.Thread(target=self.close_popup, args=[duration])
        t.start()

        lines = content.splitlines()
        self.tmux_pane.cmd("display-popup", "", *lines)
        t.join()

    def close_popup(self, duration: float = 0) -> None:
        self.pause(duration)
        self.tmux_pane.cmd("display-popup", "-C")

    def instruction(self, instruction: str, duration: float = 3, time_from: typing.Optional[float] = None) -> None:
        if time_from is None:
            time_from = self.current_time

        self.instructions.append(InstructionSpec(
            instruction = str(len(self.instructions) + 1) + ". " + instruction,
            time_from = round(time_from, 1),
            time_to = round(time_from + duration, 1)
        ))

    def save_instructions(self, output_path: str) -> None:
        instr_as_dicts = []
        for instr in self.instructions:
            instr_as_dicts.append(instr._asdict())
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(instr_as_dicts, f, ensure_ascii=False, indent=4)

    @property
    def current_time(self) -> float:
        now = time.time()
        return round(now - self.record_start, 1)

    @property
    def current_pane(self) -> libtmux.Pane:
        return self.tmux_pane
