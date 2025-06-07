import logging
import os
import platform
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple, Type

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy.log import ALERT


class BrowserConfig:
    """Configuration for browser launch parameters"""
    def __init__(
        self, 
        cmd: List[str],
        proxy_arg_format: str = "--proxy-server={}:{}",
        user_data_dir_arg: str = "--user-data-dir={}",
        default_args: List[str] = None
    ):
        self.cmd = cmd
        self.proxy_arg_format = proxy_arg_format
        self.user_data_dir_arg = user_data_dir_arg
        self.default_args = default_args or []


class BrowserFinder:
    """Base class for browser finders"""
    @classmethod
    def find_executable(cls) -> Optional[str]:
        """Find browser executable on the system"""
        raise NotImplementedError()
    
    @classmethod
    def find_flatpak(cls) -> Optional[str]:
        """Find browser flatpak on the system"""
        return None
    
    @classmethod
    def get_cmd(cls) -> Optional[List[str]]:
        """Get browser command to execute"""
        if executable := cls.find_executable():
            return [executable]
        elif flatpak := cls.find_flatpak():
            return ["flatpak", "run", "-p", flatpak]
        return None


class ChromeFinder(BrowserFinder):
    """Finder for Chrome/Chromium browsers"""
    @classmethod
    def find_executable(cls) -> Optional[str]:
        for browser in (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            # https://stackoverflow.com/questions/40674914/google-chrome-path-in-windows-10
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Application\chrome.exe",
            # Linux binary names from Python's webbrowser module.
            "google-chrome",
            "google-chrome-stable",
            "chrome",
            "chromium",
            "chromium-browser",
            "google-chrome-unstable",
        ):
            if shutil.which(browser):
                return browser
        return None

    @classmethod
    def find_flatpak(cls) -> Optional[str]:
        if shutil.which("flatpak"):
            for browser in (
                "com.google.Chrome",
                "org.chromium.Chromium",
                "com.github.Eloston.UngoogledChromium",
                "com.google.ChromeDev",
            ):
                if (
                    subprocess.run(
                        ["flatpak", "info", browser],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    ).returncode
                    == 0
                ):
                    return browser
        return None


class FirefoxFinder(BrowserFinder):
    """Finder for Firefox browsers"""
    @classmethod
    def find_executable(cls) -> Optional[str]:
        for browser in (
            "/Applications/Firefox.app/Contents/MacOS/firefox",
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            # Linux binary names
            "firefox",
            "firefox-esr",
            "firefox-developer-edition",
            "firefox-nightly",
        ):
            if shutil.which(browser):
                return browser
        return None

    @classmethod
    def find_flatpak(cls) -> Optional[str]:
        if shutil.which("flatpak"):
            for browser in (
                "org.mozilla.firefox",
                "org.mozilla.FirefoxDevEdition",
                "org.mozilla.FirefoxNightly",
            ):
                if (
                    subprocess.run(
                        ["flatpak", "info", browser],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    ).returncode
                    == 0
                ):
                    return browser
        return None


class BrowserFactory:
    """Factory to create browser configurations"""
    _browsers: Dict[str, Tuple[Type[BrowserFinder], Dict]] = {
        "chrome": (
            ChromeFinder, 
            {
                "proxy_arg_format": "--proxy-server={}:{}",
                "user_data_dir_arg": "--user-data-dir={}",
                "default_args": [
                    "--disable-fre",
                    "--no-default-browser-check",
                    "--no-first-run",
                    "--disable-extensions",
                    "about:blank",
                ]
            }
        ),
        "firefox": (
            FirefoxFinder,
            {
                "proxy_arg_format": "--proxy-server={}:{}",
                "user_data_dir_arg": "-profile",
                "default_args": [
                    "--new-instance",
                    "--no-remote",
                    "--private-window",
                    "about:blank",
                ]
            }
        )
    }

    @classmethod
    def get_browser_config(cls, browser_type: str = None) -> Optional[BrowserConfig]:
        """Get browser configuration for the specified browser type
        
        Args:
            browser_type: Type of browser to launch ('chrome', 'firefox', or None for auto-detect)
        
        Returns:
            BrowserConfig if a matching browser is found, otherwise None
        """
        # If browser type is specified, try only that browser
        if browser_type and browser_type in cls._browsers:
            finder_cls, config = cls._browsers[browser_type]
            if cmd := finder_cls.get_cmd():
                return BrowserConfig(cmd=cmd, **config)
            return None
        
        # Otherwise try browsers in order of preference
        for finder_cls, config in cls._browsers.values():
            if cmd := finder_cls.get_cmd():
                return BrowserConfig(cmd=cmd, **config)
        
        return None

    @classmethod
    def get_available_browsers(cls) -> List[str]:
        """Get list of available browser types on the system"""
        available = []
        for browser_type, (finder_cls, _) in cls._browsers.items():
            if finder_cls.get_cmd():
                available.append(browser_type)
        return available


class Browser:
    browser: list[subprocess.Popen] = []
    tdir: list[tempfile.TemporaryDirectory] = []
    browser_types: Dict[int, str] = {}  # Maps browser index to browser type

    @command.command("browser.start")
    def start(self, browser_type: str = None) -> None:
        """
        Start an isolated browser instance that points to the currently running proxy.
        
        Args:
            browser_type: Type of browser to launch ('chrome', 'firefox', or auto-detect if not specified)
        """
        if len(self.browser) > 0:
            logging.log(ALERT, "Starting additional browser")

        browser_config = BrowserFactory.get_browser_config(browser_type)
        if not browser_config:
            available = BrowserFactory.get_available_browsers()
            if available:
                msg = f"Browser '{browser_type}' not found. Available browsers: {', '.join(available)}"
            else:
                msg = "No supported browsers found on your platform - please submit a patch."
            logging.log(ALERT, msg)
            return

        # Create temporary directory for browser profile
        tdir = tempfile.TemporaryDirectory()
        self.tdir.append(tdir)
        
        # Prepare proxy arguments
        proxy_arg = browser_config.proxy_arg_format.format(
            ctx.options.listen_host or "127.0.0.1",
            ctx.options.listen_port or "8080"
        )
        
        # Prepare user data directory argument
        user_data_arg = browser_config.user_data_dir_arg.format(tdir.name)
        
        # Construct the command with all arguments
        cmd = [
            *browser_config.cmd,
            user_data_arg,
            proxy_arg,
            *browser_config.default_args
        ]
        
        # Launch the browser
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        # Store the browser process and type
        browser_idx = len(self.browser)
        self.browser.append(process)
        
        # Determine the browser type from the configuration
        detected_type = "unknown"
        for btype, (finder_cls, _) in BrowserFactory._browsers.items():
            if isinstance(browser_config.cmd[0], str) and browser_config.cmd[0].lower().find(btype) != -1:
                detected_type = btype
                break
                
        self.browser_types[browser_idx] = browser_type or detected_type
        
        logging.log(ALERT, f"Started {self.browser_types[browser_idx]} browser")

    @command.command("browser.list")
    def list(self) -> str:
        """List running browser instances"""
        if not self.browser:
            return "No browsers running"
        
        result = []
        for idx, process in enumerate(self.browser):
            browser_type = self.browser_types.get(idx, "unknown")
            status = "running" if process.poll() is None else f"exited (code {process.returncode})"
            result.append(f"Browser {idx}: {browser_type} - {status}")
        
        return "\n".join(result)

    @command.command("browser.stop")
    def stop(self, browser_idx: int = -1) -> None:
        """
        Stop a running browser instance
        
        Args:
            browser_idx: Index of browser to stop, or -1 to stop the most recently started browser
        """
        if not self.browser:
            logging.log(ALERT, "No browsers running")
            return
            
        if browser_idx < 0:
            browser_idx = len(self.browser) - 1
            
        if browser_idx >= len(self.browser):
            logging.log(ALERT, f"Invalid browser index: {browser_idx}")
            return
            
        # Kill the browser process
        process = self.browser[browser_idx]
        browser_type = self.browser_types.get(browser_idx, "unknown")
        
        if process.poll() is None:
            process.kill()
            logging.log(ALERT, f"Stopped {browser_type} browser (index {browser_idx})")
        else:
            logging.log(ALERT, f"Browser already exited (index {browser_idx})")

        # Cleanup temporary directory
        if browser_idx < len(self.tdir):
            self.tdir[browser_idx].cleanup()
        
    def done(self):
        """Clean up all browser instances when mitmproxy exits"""
        for browser in self.browser:
            if browser.poll() is None:
                browser.kill()
        for tdir in self.tdir:
            tdir.cleanup()
        self.browser = []
        self.tdir = []
        self.browser_types = {}
