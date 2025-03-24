import copy
import json
import logging
import tempfile
from datetime import datetime
from datetime import timezone
from threading import Lock

from mitmproxy.addons.browserup.har.har_builder import HarBuilder
from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes
from mitmproxy.net.http import cookies

mutex = Lock()

SUBMITTED_FLAG = "_submitted"


class HarManagerMixin:
    # Used to manage a single active har, gets mixed into har_capture_addon

    def __init__(self):
        self.page_number = 0
        self.har = HarBuilder.har()

        self.har_capture_types = [
            HarCaptureTypes.REQUEST_HEADERS,
            HarCaptureTypes.REQUEST_COOKIES,
            HarCaptureTypes.REQUEST_CONTENT,
            HarCaptureTypes.REQUEST_BINARY_CONTENT,
            HarCaptureTypes.RESPONSE_HEADERS,
            HarCaptureTypes.RESPONSE_COOKIES,
            HarCaptureTypes.RESPONSE_DYNAMIC_CONTENT,
            HarCaptureTypes.WEBSOCKET_MESSAGES,
        ]
        #  omitting HarCaptureTypes.RESPONSE_BINARY_CONTENT,
        self.http_connect_timings = {}

    def get_or_create_har(self, page_ref=None, page_title=None):
        if self.har is None:
            self.reset_har_and_return_old_har()
        return self.har

    def new_har(self):
        self.har = HarBuilder.har()

    def create_har_entry(self, flow):
        har = self.get_or_create_har()
        page = self.get_or_create_current_page()
        pageref = page["id"]
        entry = HarBuilder.entry(pageref)
        har["log"]["entries"].append(entry)
        self.print_har_summary()
        return entry

    def get_har(self, clean_har):
        if clean_har:
            self.new_har()
        return self.har

    def new_page(self, page_title=None, page_ref=None):
        logging.info("-->Creating new page")

        # only create a new page if there are entries in the current page
        if len(self.har["log"]["pages"]) > 0:
            self.end_page()

        har = self.get_or_create_har()

        next_page_number = len(har["log"]["pages"]) + 1
        next_id = "page_{}".format(next_page_number)
        new_page = HarBuilder.page(id=next_id)
        har["log"]["pages"].append(new_page)

    # print a list of the pages with their title and a list of the entries, and their page ref
    def print_har_summary(self):
        return
        logging.debug("-->Printing har summary")
        h = self.get_or_create_har()
        for page in h["log"]["pages"]:
            logging.debug(page["title"] + " " + page["id"])
            for entry in h["log"]["entries"]:
                logging.info("===>entry: {}".format(entry))

    def get_current_page_ref(self):
        har_page = self.get_or_create_current_page()
        return har_page["id"]

    def get_or_create_current_page(self):
        self.get_or_create_har()
        if len(self.har["log"]["pages"]) > 0:
            return self.har["log"]["pages"][-1]
        else:
            har_page = HarBuilder.page
            self.har["log"]["pages"].append(har_page)
            return har_page

    def reset_har_and_return_old_har(self):
        logging.info("Creating new har")

        with mutex:
            old_har = self.end_har()
            self.har = HarBuilder.har()

        return old_har

    def add_verification_to_har(self, verification_type, verification_name, result):
        self.add_custom_value_to_har(
            "_verifications",
            {"name": verification_name, "type": verification_type, "result": result},
        )

    def add_metric_to_har(self, metric_dict):
        self.add_custom_value_to_har("_metrics", metric_dict)

    def add_error_to_har(self, error_dict):
        self.add_custom_value_to_har("_errors", error_dict)

    def add_page_timings_to_har(self, page_info):
        page = self.get_or_create_current_page()
        timings = page["pageTimings"]
        timings.update(page_info)
        page["pageTimings"] = timings
        logging.info(self.get_or_create_current_page())

    def add_page_data_to_har(self, page_data):
        page = self.get_or_create_current_page()
        # one-liner to merge page data into page giving precedence to page data
        page.update(page_data)

    def entries_for_page(self, page_ref):
        har = self.get_or_create_har()
        return [
            entry for entry in har["log"]["entries"] if entry["pageref"] == page_ref
        ]

    def page_from_page_ref(self, page_ref):
        har = self.get_or_create_har()
        for page in har["log"]["pages"]:
            if page["id"] == page_ref:
                return page

    def is_a_websocket(self, entry):
        # check if the request is a websocket by checking headers for upgrade: websocket
        for header in entry["response"]["headers"]:
            if (
                header["name"].lower() == "upgrade"
                and header["value"].lower() == "websocket"
            ):
                return True

    # not guaranteed
    def is_a_video(self, entry):
        url = entry["request"]["url"]

        video_extensions = [".mp4", ".webm", ".ogg", ".flv", ".avi"]
        if any(url.lower().endswith(ext) for ext in video_extensions):
            return True

        mime_type = ""
        for header in entry["response"]["headers"]:
            if header["name"].lower() == "content-type":
                mime_type = header["value"]
                break

        if "video" in mime_type:
            return True

        return False

    def submit_har(self):
        page = self.get_or_create_current_page()
        self.submit_entries(page["id"], True, True)
        self.submit_page(page)

    def decorate_video_data_on_entries(self, video_data):
        page = self.get_or_create_current_page()
        latest_page_entries = self.entries_for_page(page["id"])
        if len(latest_page_entries) == 0 or len(video_data) == 0:
            return

        for entry in latest_page_entries:
            for video in video_data:
                videosrc = video["_videoSRC"]
                if not videosrc or videosrc == "":
                    continue

                if videosrc in entry["request"]["url"]:
                    print("found video entry! {}".format(entry))
                    del video["_videoSRC"]
                    entry["response"]["content"].update(video)
                    video_data.remove(video)  # remove the video from the video_data
                    break

    def add_custom_value_to_har(self, item_type, item):
        page = self.get_or_create_current_page()
        page.setdefault(item_type, [])
        items = page.get(item_type)
        items.append(item)

    def set_page_title(self, title):
        logging.debug("Setting page title to: {}".format(title))
        page = self.get_or_create_current_page()
        page["title"] = title

    def end_har(self):
        logging.info("Ending current har...")
        self.end_page()
        old_har = self.har
        self.har = HarBuilder.har()
        return old_har

    def copy_entries_without_response(self, old_har):
        if old_har is not None:
            for entry in old_har["log"]["entries"]:
                if not self.har_entry_has_response(entry):
                    self.har["log"]["entries"].append(entry)

    def end_page(self):
        logging.info("Ending current page...")

    def is_har_entry_submitted(self, har_entry):
        return har_entry.get(SUBMITTED_FLAG)

    def har_entry_has_response(self, har_entry):
        return bool(har_entry["response"])

    # normally, for responses, we only submit when 'done' (have a response) and they are not websockets or videos
    # because websocket and video responses may be ongoing until the page is exited (next page started)
    # however, we do want to submit websocket messages and video data, so we pass the flags to include them
    # when we are done with the page (a final submit).

    def create_filtered_har_and_track_submitted(
        self, report_last_page=False, include_websockets=False, include_videos=False
    ):
        if self.har is None:
            return None

        entries_to_report = []

        for entry in self.har["log"]["entries"]:
            request_copy = {}
            response_copy = {}

            # always submit request unless already submitted
            if not entry["request"].get(SUBMITTED_FLAG):
                request_copy = copy.deepcopy(entry["request"])
                entry["request"][SUBMITTED_FLAG] = True

            if entry["response"]:
                # delay websocket harvesting until we have all messages
                if not entry["response"].get(SUBMITTED_FLAG):
                    if (include_websockets or not self.is_a_websocket(entry)) and (
                        include_videos or not self.is_a_video(entry)
                    ):
                        response_copy = copy.deepcopy(entry["response"])
                        entry["response"][SUBMITTED_FLAG] = True

                if request_copy or response_copy:
                    entry_copy = copy.deepcopy(entry)
                    entry_copy["request"] = request_copy
                    entry_copy["response"] = response_copy
                    entries_to_report.append(entry_copy)

        pages_to_report = []

        pages = (
            self.har["log"]["pages"]
            if report_last_page
            else self.har["log"]["pages"][:-1]
        )
        for page in pages:
            if not page.get(SUBMITTED_FLAG):
                page_copy = copy.deepcopy(page)
                pages_to_report.append(page_copy)
                page[SUBMITTED_FLAG] = True

        har_copy = copy.deepcopy(self.har)
        har_copy["log"]["entries"] = entries_to_report
        har_copy["log"]["pages"] = pages_to_report
        return har_copy

    def _likely_a_video(entry):
        url = entry["request"]["url"]
        mime_type = ""
        for header in entry["response"]["headers"]:
            if header["name"].lower() == "content-type":
                mime_type = header["value"]
                break

        if "video" in mime_type:
            return True

        video_extensions = [".mp4", ".webm", ".ogg", ".flv", ".avi"]
        if any(url.lower().endswith(ext) for ext in video_extensions):
            return True

        return False

    def format_cookies(self, cookie_list):
        rv = []

        for name, value, attrs in cookie_list:
            cookie_har = {
                "name": name,
                "value": value,
            }

            # HAR only needs some attributes
            for key in ["path", "domain", "comment"]:
                if key in attrs:
                    cookie_har[key] = attrs[key]

            # These keys need to be boolean!
            for key in ["httpOnly", "secure"]:
                cookie_har[key] = bool(key in attrs)

            # Expiration time needs to be formatted
            expire_ts = cookies.get_expiration_ts(attrs)
            if expire_ts is not None:
                cookie_har["expires"] = datetime.fromtimestamp(
                    expire_ts, timezone.utc
                ).isoformat()

            rv.append(cookie_har)

        return rv

    def save_har(self, har):
        json_dump: str = json.dumps(har, ensure_ascii=True, indent=2)

        tmp_file = tempfile.NamedTemporaryFile(
            mode="wb", prefix="har_dump_", delete=False
        )
        raw: bytes = json_dump.encode()
        tmp_file.write(raw)
        tmp_file.flush()
        tmp_file.close()

        return tmp_file

    def save_current_har_to_path(self, full_path):
        json_dump: str = json.dumps(self.har, indent=2)

        with open(full_path, "wb") as file:
            raw: bytes = json_dump.encode()
            file.write(raw)
            file.flush()
            file.close()

    def format_request_cookies(self, fields):
        return self.format_cookies(cookies.group_cookies(fields))

    def format_response_cookies(self, fields):
        return self.format_cookies((c[0], c[1][0], c[1][1]) for c in fields)

    def name_value(self, obj):
        """
        Convert (key, value) pairs to HAR format.
        """
        return [{"name": k, "value": v} for k, v in obj.items()]
