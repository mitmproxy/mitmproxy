# Release History

## 28 September 2021: mitmproxy 7.0.4

* Do not add a Content-Length header for chunked HTTP/1 messages (@matthewhughes934)

## 16 September 2021: mitmproxy 7.0.3

* [CVE-2021-39214](https://github.com/mitmproxy/mitmproxy/security/advisories/GHSA-22gh-3r9q-xf38):
  Fix request smuggling vulnerabilities reported by @chinchila (@mhils)
* Expose TLS 1.0 as possible minimum version on older pyOpenSSL releases (@mhils)
* Fix compatibility with Python 3.10 (@mhils)

## 4 August 2021: mitmproxy 7.0.2

* Fix a WebSocket crash introduced in 7.0.1 (@mhils)

## 3 August 2021: mitmproxy 7.0.1

* Performance: Re-use OpenSSL contexts to enable TLS session resumption (@mhils)
* Disable HTTP/2 CONNECT for Secure Web Proxies to fix compatibility with Firefox (@mhils)
* Use local IP address as certificate subject if no other info is available (@mhils)
* Make it possible to return multiple chunks for HTTP stream modification (@mhils)
* Don't send WebSocket CONTINUATION frames when the peer does not send any (@Pilphe)
* Fix HTTP stream modify example. (@mhils)
* Fix a crash caused by no-op assignments to `Server.address` (@SaladDais)
* Fix a crash when encountering invalid certificates (@mhils)
* Fix a crash when pressing the Home/End keys in some screens (@rbdixon)
* Fix a crash when reading corrupted flow dumps (@mhils)
* Fix multiple crashes on flow export (@mhils)
* Fix a bug where ASGI apps did not see the request body (@mhils)
* Minor documentation improvements (@mhils)

## 16 July 2021: mitmproxy 7.0

### New Proxy Core (@mhils, [blog post](https://www.mitmproxy.org/posts/releases/mitmproxy7/))

Mitmproxy has a completely new proxy core, fixing many longstanding issues:

* **Secure Web Proxy:** Mitmproxy now supports TLS-over-TLS to already encrypt the connection to the proxy.
* **Server-Side Greetings:** Mitmproxy now supports proxying raw TCP connections, including ones that start
  with a server-side greeting (e.g. SMTP).
* **HTTP/1 – HTTP/2 Interoperability:** mitmproxy can now accept an HTTP/2 connection from the client,
  and forward it to an HTTP/1 server.
* **HTTP/2 Redirects:** The request destination can now be changed on HTTP/2 flows.
* **Connection Strategy:** Users can now specify if they want mitmproxy to eagerly connect upstream
  or wait as long as possible. Eager connections are required to detect protocols with server-side
  greetings, lazy connections enable the replay of responses without connecting to an upstream server.
* **Timeout Handling:** Mitmproxy will now clean up idle connections and also abort requests if the client disconnects
  in the meantime.
* **Host Header-based Proxying:** If the request destination is unknown, mitmproxy now falls back to proxying
  based on the Host header. This means that requests can often be redirected to mitmproxy using
  DNS spoofing only.
* **Internals:** All protocol logic is now separated from I/O (["sans-io"](https://sans-io.readthedocs.io/)).
  This greatly improves testing capabilities, prevents a wide array of race conditions, and increases
  proper isolation between layers.

### Additional Changes

* mitmproxy's command line interface now supports Windows (@mhils)
* The `clientconnect`, `clientdisconnect`, `serverconnect`, `serverdisconnect`, and `log`
  events have been replaced with new events, see addon documentation for details (@mhils)
* Contentviews now implement `render_priority` instead of `should_render`, allowing more specialization (@mhils)
* Addition of block_list option to block requests with a set status code (@ericbeland)
* Make mitmweb columns configurable and customizable (@gorogoroumaru)
* Automatic JSON view mode when `+json` suffix in content type (@kam800)
* Use pyca/cryptography to generate certificates, not pyOpenSSL (@mhils)
* Remove the legacy protocol stack (@Kriechi)
* Remove all deprecated pathod and pathoc tools and modules (@Kriechi)
* In reverse proxy mode, mitmproxy now does not assume TLS if no scheme
  is given but a custom port is provided (@mhils)
* Remove the following options: `http2_priority`, `relax_http_form_validation`, `upstream_bind_address`,
  `spoof_source_address`, and `stream_websockets`. If you depended on one of them please let us know.
  mitmproxy never phones home, which means we don't know how prominently these options were used. (@mhils)
* Fix IDNA host 'Bad HTTP request line' error (@grahamrobbins)
* Pressing `?` now exits console help view (@abitrolly)
* `--modify-headers` now works correctly when modifying a header that is also part of the filter expression (@Prinzhorn)
* Fix SNI-related reproducibility issues when exporting to curl/httpie commands. (@dkasak)
* Add option `export_preserve_original_ip` to force exported command to connect to IP from original request.
  Only supports curl at the moment. (@dkasak)
* Major proxy protocol testing (@r00t-)
* Switch Docker image release to be based on Debian (@PeterDaveHello)
* Multiple Browsers: The `browser.start` command may be executed more than once to start additional
  browser sessions. (@rbdixon)
* Improve readability of SHA256 fingerprint. (@wrekone)
* Metadata and Replay Flow Filters: Flows may be filtered based on metadata and replay status. (@rbdixon)
* Flow control: don't read connection data faster than it can be forwarded. (@hazcod)
* Docker images for ARM64 architecture (@hazcod, @mhils)
* Fix parsing of certificate issuer/subject with escaped special characters (@Prinzhorn)
* Customize markers with emoji, and filters: The `flow.mark` command may be used to mark a flow with either the default
  "red ball" marker, a single character, or an emoji like `:grapes:`. Use the `~marker` filter to filter on marker
  characters. (@rbdixon)
* New `flow.comment` command to add a comment to the flow. Add `~comment <regex>` filter syntax to search flow comments.
  (@rbdixon)
* Fix multipart forms losing `boundary` values on edit. (@roytu)
* `Transfer-Encoding: chunked` HTTP message bodies are now retained if they are below the stream_large_bodies limit.
  (@mhils)
* `json()` method for HTTP Request and Response instances will return decoded JSON body. (@rbdixon)
* Support for HTTP/2 Push Promises has been dropped. (@mhils)
* Make it possible to set sequence options from the command line. (@Yopi)

## 15 December 2020: mitmproxy 6.0.2

* Fix reading of saved flows in mitmweb.

## 13 December 2020: mitmproxy 6.0.1

* Fix flow serialization in mitmweb.

## 13 December 2020: mitmproxy 6.0

* Mitmproxy now requires Python 3.8 or above.
* Deprecation of pathod and pathoc tools and modules. Future releases will not contain them! (@Kriechi)
* SSLKEYLOGFILE now supports TLS 1.3 secrets (@mhils)
* Fix query parameters in asgiapp addon (@jpstotz)
* Fix command history failing on file I/O errors (@Kriechi)
* Add example addon to suppress unwanted error messages sent by mitmproxy. (@anneborcherding)
* Updated imports and styles for web scanner helper addons. (@anneborcherding)
* Inform when underscore-formatted options are used in client arg. (@jrblixt)
* ASGIApp now ignores loaded HTTP flows from somewhere. (@linw1995)
* Binaries are now built with Python 3.9 (@mhils)
* Fixed the web UI showing blank page on clicking details tab when server address is missing (@samhita-sopho)
* Tests: Replace asynctest with stdlib mock (@felixonmars)
* MapLocal now keeps its configuration when other options are set. (@mhils)
* Host headers with non-standard ports are now properly updated in reverse proxy mode. (@mhils)
* Fix missing host header when replaying HTTP/2 flows (@Granitosaurus)

## 01 November 2020: mitmproxy 5.3

### Full Changelog

* Support for Python 3.9 (@mhils)
* Add MsgPack content viewer (@tasn)
* Use `@charset` to decode CSS files if available (@Prinzhorn)
* Fix links to anticache docs in mitmweb and use HTTPS for links to documentation (@rugk)
* Updated typing for WebsocketMessage.content (@Prinzhorn)
* Add option `console_strip_trailing_newlines`, and no longer strip trailing newlines by default (@capt8bit)
* Prevent transparent mode from connecting to itself in the basic cases (@Prinzhorn)
* Display HTTP trailers in mitmweb (@sanlengjingvv)
* Revamp onboarding app (@mhils)
* Add ASGI support for embedded apps (@mhils)
* Updated raw exports to not remove headers (@wchasekelley)
* Fix file unlinking before external viewer finishes loading (@wchasekelley)
* Add --cert-passphrase command line argument (@mirosyn)
* Add interactive tutorials to the documentation (@mplattner)
* Support `deflateRaw` for `Content-Encoding`'s (@kjoconnor)
* Fix broken requests without body on HTTP/2 (@Kriechi)
* Add support for sending (but not parsing) HTTP Trailers to the HTTP/1.1 protocol (@bburky)
* Add support to echo http trailers in dumper addon (@shiv6146)
* Fix OpenSSL requiring different CN for root and leaf certificates (@mhils)
* ... and various other fixes, documentation improvements, dependency version bumps, etc.

## 18 July 2020: mitmproxy 5.2

* Add Filter message to mitmdump (@sarthak212)
* Display TCP flows at flow list (@Jessonsotoventura, @nikitastupin, @mhils)
* Colorize JSON Contentview (@sarthak212)
* Fix console crash when entering regex escape character in half-open string (@sarthak212)
* Integrate contentviews to TCP flow details (@nikitastupin)
* Added add-ons that enhance the performance of web application scanners (@anneborcherding)
* Increase WebSocket message timestamp precision (@JustAnotherArchivist)
* Fix HTTP reason value on HTTP/2 reponses (@rbdixon)
* mitmweb: support wslview to open a web browser (@G-Rath)
* Fix dev version detection with parent git repo (@JustAnotherArchivist)
* Restructure examples and supported addons (@mhils)
* Certificate generation: mark SAN as critical if no CN is set (@mhils)
* Simplify Replacements with new ModifyBody addon (@mplattner)
* Rename SetHeaders addon to ModifyHeaders (@mplattner)
* mitmweb: "New -> File" menu option has been renamed to "Clear All" (@yogeshojha)
* Add new MapRemote addon to rewrite URLs of requests (@mplattner)
* Add support for HTTP Trailers to the HTTP/2 protocol (@sanlengjingvv and @Kriechi)
* Fix certificate runtime error during expire cleanup (@gorogoroumaru)
* Fixed the DNS Rebind Protection for secure support of IPv6 addresses (@tunnelpr0)
* WebSockets: match the HTTP-WebSocket flow for the ~websocket filter (@Kriechi)
* Fix deadlock caused by the "replay.client.stop" command (@gorogoroumaru)
* Add new MapLocal addon to serve local files instead of remote resources (@mplattner and @mhils)
* Add minimal TCP interception and modification (@nikitastupin)
* Add new CheckSSLPinning addon to check SSL-Pinning on client (@su-vikas)
* Add a JSON dump script: write data into a file or send to an endpoint as JSON (@emedvedev)
* Fix console output formatting (@sarthak212)
* Add example for proxy authentication using selenium (@anneborcherding and @weichweich)

## 13 April 2020: mitmproxy 5.1.1

* Fixed Docker images not starting due to missing shell

## 13 April 2020: mitmproxy 5.1

### Major Changes

* Initial Support for TLS 1.3

### Full Changelog

* Reduce leaf certificate validity to one year due to upcoming browser changes (@mhils)
* Rename mitmweb's `web_iface` option to `web_host` for consistency (@oxr463)
* Sending a SIGTERM now exits mitmproxy without prompt, SIGINT still asks (@ThinkChaos)
* Don't force host header on outgoing requests (@mhils)
* Additional documentation and examples for WebSockets (@Kriechi)
* Gracefully handle hyphens in domain names (@matosconsulting)
* Fix header replacement count (@naivekun)
* Emit serverconnect event only after a connection has been established (@Prinzhorn)
* Fix ValueError in table mode of server replay flow (@ylmrx)
* HTTP/2: send all stream reset types to other connection (@rohfle)
* HTTP/2: fix WINDOW_UPDATE swallowed on closed streams (@Kriechi)
* Fix wrong behavior of --allow-hosts options (@BlownSnail)
* Additional and updated documentation for examples, WebSockets, Getting Started (@Kriechi)

## 27 December 2019: mitmproxy 5.0.1

* Fixed precompiled Linux binaries to not crash in table mode
* Display webp images in mitmweb (@cixtor)

## 16 December 2019: mitmproxy 5.0

### Major Changes

* Added new Table UI (@Jessonsotoventura)
* Added EKU extension to certificates. This fixes support for macOS Catalina (@vin01)

### Security Fixes

* Fixed command injection vulnerabilities when exporting flows as curl/httpie commands (@cript0nauta)
* Do not echo unsanitized user input in HTTP error responses (@fimad)

### Full Changelog

* Moved to GitHub CI for Continuous Integration, dropping support for old Linux and macOS releases. (#3728)
* Vastly improved command parsing, in particular for setting flow filters (@typoon)
* Added a new flow export for raw responses (@mckeimic)
* URLs are now edited in an external editor (@Jessonsotoventura)
* mitmproxy now has a command history (@typoon)
* Added terminal like keyboard shortcuts for the command bar (ctrl+w, ctrl+a, ctrl+f, ...) (@typoon)
* Fixed issue with improper handling of non-ascii characters in URLs (@rjt-gupta)
* Filtering can now use unicode characters (@rjt-gupta)
* Fixed issue with user keybindings not being able to override default keybindings
* Improved installation instructions
* Added support for IPV6-only environments (@sethb157)
* Fixed bug with server replay (@rjt-gupta)
* Fixed issue with duplicate error responses (@ccssrryy)
* Users can now set a specific external editor using $MITMPROXY_EDITOR (@rjt-gupta)
* Config file can now be called `config.yml` or `config.yaml` (@ylmrx)
* Fixed crash on `view.focus.[next|prev]` (@ylmrx)
* Updated documentation to help using mitmproxy certificate on Android (@jannst)
* Added support to parse IPv6 entries from `pfctl` on MacOS. (@tomlabaude)
* Fixed instructions on how to build the documentation (@jannst)
* Added a new `--allow-hosts` option (@pierlon)
* Added support for zstd content-encoding (@tsaaristo)
* Fixed issue where the replay server would corrupt the Date header (@tonyb486)
* Improve speed for WebSocket interception (@MathieuBordere)
* Fixed issue with parsing JPEG files. (@lusceu)
* Improve example code style (@BoboTiG)
* Fixed issue converting void responses to HAR (@worldmind)
* Color coded http status codes in mitmweb (@arun-94)
* Added organization to generated certificates (@Abcdefghijklmnopqrstuvwxyzxyz)
* Errors are now displayed on sys.stderr (@JessicaFavin)
* Fixed issue with replay timestamps (@rjt-gupta)
* Fixed copying in mitmweb on macOS (@XZzYassin)

## 31 July 2018: mitmproxy 4.0.4

* Security: Protect mitmweb against DNS rebinding. (CVE-2018-14505, @atx)
* Reduce certificate lifetime to two years to be conformant with
  the current CA/Browser Forum Baseline Requirements. (@muffl0n)
  (https://cabforum.org/2017/03/17/ballot-193-825-day-certificate-lifetimes/)
* Update cryptography to version 2.3.

## 15 June 2018: mitmproxy 4.0.3

* Add support for IPv6 transparent mode on Windows (#3174)
* Add Docker images for ARMv7 - Raspberry Pi (#3190)
* Major overhaul of our release workflow - you probably won't notice it, but for us it's a big thing!
* Fix the Python version detection on Python 3.5, we now show a more intuitive error message (#3188)
* Fix application shutdown on Windows (#3172)
* Fix IPv6 scope suffixes in block addon (#3164)
* Fix options update when added (#3157)
* Fix "Edit Flow" button in mitmweb (#3136)

## 15 June 2018: mitmproxy 4.0.2

* Skipped!

## 17 May 2018: mitmproxy 4.0.1

### Bugfixes

* The previous release had a packaging issue, so we bumped it to v4.0.1 and re-released it.
* This contains no actual bugfixes or new features.

## 17 May 2018: mitmproxy 4.0

### Features

* mitmproxy now requires Python 3.6!
* Moved the core to asyncio - which gives us a very significant performance boost!
* Reduce memory consumption by using `SO_KEEPALIVE` (#3076)
* Export request as httpie command (#3031)
* Configure mitmproxy console keybindings with the keys.yaml file. See docs for more.

### Breaking Changes

* The --conf command-line flag is now --confdir, and specifies the mitmproxy configuration
    directory, instead of the options yaml file (which is at `config.yaml` under the configuration directory).
* `allow_remote` got replaced by `block_global` and `block_private` (#3100)
* No more custom events (#3093)
* The `cadir` option has been renamed to `confdir`
* We no longer magically capture print statements in addons and translate
    them to logs. Please use `ctx.log.info` explicitly.

### Bugfixes

* Correctly block connections from remote clients with IPv4-mapped IPv6 client addresses (#3099)
* Expand `~` in paths during the `cut` command (#3078)
* Remove socket listen backlog constraint
* Improve handling of user script exceptions (#3050, #2837)
* Ignore signal errors on windows
* Fix traceback for commands with un-terminated escape characters (#2810)
* Fix request replay when proxy is bound to local interface (#2647)
* Fix traceback when running scripts on a flow twice (#2838)
* Fix traceback when killing intercepted flow (#2879)
* And lots of typos, docs improvements, revamped examples, and general fixes!

## 05 April 2018: mitmproxy 3.0.4

* Fix an issue that caused mitmproxy to not retry HTTP requests on timeout.
* Various other fixes (@kira0204, @fenilgandhi, @tran-tien-dat, @smonami,
  @luzpaz, @fristonio, @kajojify, @Oliver-Fish, @hcbarry, @jplochocki, @MikeShi42,
  @ghillu, @emilstahl)

## 25 February 2018: mitmproxy 3.0.3

* Fix an issue that caused mitmproxy to lose keyboard control after spawning an external editor.

## 23 February 2018: mitmproxy 3.0.1

* Fix a quote-related issue affecting the mitmproxy console command prompt.

## 22 February 2018: mitmproxy 3.0

### Major Changes

* Commands: A consistent, typed mechanism that allows addons to expose actions
  to users.
* Options: A typed settings store for use by mitmproxy and addons.
* Shift most of mitmproxy's own functionality into addons.
* Major improvements to mitmproxy console, including an almost complete
  rewrite of the user interface, integration of commands, key bindings, and
  multi-pane layouts.
* Major Improvements to mitmproxy’s web interface, mitmweb. (Matthew Shao,
  Google Summer of Code 2017)
* Major Improvements to mitmproxy’s content views and protocol layers (Ujjwal
  Verma, Google Summer of Code 2017)
* Faster JavaScript and CSS beautifiers. (Ujjwal Verma)

### Minor Changes

* Vastly improved JavaScript test coverage (Matthew Shao)
* Options editor for mitmweb (Matthew Shao)
* Static web-based flow viewer (Matthew Shao)
* Request streaming for HTTP/1.x and HTTP/2 (Ujjwal Verma)
* Implement more robust content views using Kaitai Struct (Ujjwal Verma)
* Protobuf decoding now works without protoc being installed on the host
  system (Ujjwal Verma)
* PNG, GIF, and JPEG can now be parsed without Pillow, which simplifies
  mitmproxy installation and moves parsing from unsafe C to pure Python (Ujjwal Verma)
* Add parser for ICO files (Ujjwal Verma)
* Migrate WebSockets implementation to wsproto. This reduces code size and
  adds WebSocket compression support. (Ujjwal Verma)
* Add “split view” to split mitmproxy’s UI into two separate panes.
* Add key binding viewer and editor
* Add a command to spawn a preconfigured Chrome browser instance from
  mitmproxy
* Fully support mitmproxy under the Windows Subsystem for Linux (WSL), work
  around display errors
* Add XSS scanner addon (@ddworken)
* Add ability to toggle interception (@mattweidner)
* Numerous documentation improvements (@pauloromeira, @rst0git, @rgerganov,
  @fulldecent, @zhigang1992, @F1ashhimself, @vinaydargar, @jonathanrfisher1,
  @BasThomas, @LuD1161, @ayamamori, @TomTasche)
* Add filters for websocket flows (@s4chin)
* Make it possible to create a response to CONNECT requests in http_connect
  (@mengbiping)
* Redirect stdout in scripts to ctx.log.warn (@nikofil)
* Fix a crash when clearing the event log (@krsoninikhil)
* Store the generated certificate for each flow (@dlenski)
* Add --keep-host-header to retain the host header in reverse proxy mode
  (@krsoninikhil)
* Fix setting palette options (@JordanLoehr)
* Fix a crash with brotli encoding (@whackashoe)
* Provide certificate installation instructions on mitm.it (@ritiek)
* Fix a bug where we did not properly fall back to IPv4 when IPv6 is unavailable (@titeuf87)
* Fix transparent mode on IPv6-enabled macOS systems (@Ga-ryo)
* Fix handling of HTTP messages with multiple Content-Length headers (@surajt97)
* Fix IPv6 authority form parsing in CONNECT requests (@r1b)
* Fix event log display in mitmweb (@syahn)
* Remove private key from PKCS12 file in ~/.mitmproxy (@ograff).
* Add LDAP as a proxy authentication backend (@charlesdhdt)
* Use mypy to check the whole codebase (@iharsh234)
* Fix a crash when duplicating flows (@iharsh234)
* Fix testsuite when the path contains a “.” (@felixonmars)
* Store proxy authentication with flows (@lymanZerga11)
* Match ~d and ~u filters against pretty_host (@dequis)
* Update WBXML content view (@davidpshaw)
* Handle HEAD requests for mitm.it to support Chrome in transparent mode on
  iOS (@tomlabaude)
* Update dns spoofing example to use --keep-host-header (@krsoninikhil)
* Call error handler on HTTPException (@tarnacious)
* Make it possible to remove TLS from upstream HTTP connections
* Update to pyOpenSSL 17.5, cryptography 2.1.4, and OpenSSL 1.1.0g
* Make it possible to retroactively increase log verbosity.
* Make logging from addons thread-safe
* Tolerate imports in user scripts that match hook names
  (`from mitmproxy import log`)
* Update mitmweb to React 16, which brings performance improvements
* Fix a bug where reverting duplicated flows crashes mitmproxy
* Fix a bug where successive requests are sent to the wrong host after a
  request has been redirected.
* Fix a bug that binds outgoing connections to the wrong interface
* Fix a bug where custom certificates are ignored in reverse proxy mode
* Fix import of flows that have been created with mitmproxy 0.17
* Fix formatting of (IPv6) IP addresses in a number of places
* Fix replay for HTTP/2 flows
* Decouple mitmproxy version and flow file format version
* Fix a bug where “mitmdump -nr” does not exit automatically
* Fix a crash when exporting flows to curl
* Fix formatting of sticky cookies
* Improve script reloading reliability by polling the filesystem instead of using watchdog
* Fix a crash when refreshing Set-Cookie headers
* Add connection indicator to mitmweb to alert users when the proxy server stops running
* Add support for certificates with cyrillic domains
* Simplify output of mitmproxy --version
* Add Request.make to simplify request creation in scripts
* Pathoc: Include a host header on CONNECT requests
* Remove HTML outline contentview (#2572)
* Remove Python and Locust export (#2465)
* Remove emojis from tox.ini because flake8 cannot parse that. :(

## 28 April 2017: mitmproxy 2.0.2

* Fix mitmweb's Content-Security-Policy to work with Chrome 58+
* HTTP/2: actually use header normalization from hyper-h2

## 15 March 2017: mitmproxy 2.0.1

* bump cryptography dependency
* bump pyparsing dependency
* HTTP/2: use header normalization from hyper-h2

## 21 February 2017: mitmproxy 2.0

* HTTP/2 is now enabled by default.
* Image ContentView: Parse images with Kaitai Struct (kaitai.io) instead of Pillow.
  This simplifies installation, reduces binary size, and allows parsing in pure Python.
* Web: Add missing flow filters.
* Add transparent proxy support for OpenBSD.
* Check the mitmproxy CA for expiration and warn the user to regenerate it if necessary.
* Testing: Tremendous improvements, enforced 100% coverage for large parts of the
  codebase, increased overall coverage.
* Enforce individual coverage: one source file -> one test file with 100% coverage.
* A myriad of other small improvements throughout the project.
* Numerous bugfixes.

## 26 December 2016: mitmproxy 1.0

* All mitmproxy tools are now Python 3 only! We plan to support Python 3.5 and higher.
* Web-Based User Interface: Mitmproxy now officially has a web-based user interface
  called mitmweb. We consider it stable for all features currently exposed
  in the UI, but it still misses a lot of mitmproxy’s options.
* Windows Compatibility: With mitmweb, mitmproxy is now usable on Windows.
  We are also introducing an installer (kindly sponsored by BitRock) that
  simplifies setup.
* Configuration: The config file format is now a single YAML file. In most cases,
  converting to the new format should be trivial - please see the docs for
  more information.
* Console: Significant UI improvements - including sorting of flows by
  size, type and url, status bar improvements, much faster indentation for
  HTTP views, and more.
* HTTP/2: Significant improvements, but is temporarily disabled by default
  due to wide-spread protocol implementation errors on some large website
* WebSocket: The protocol implementation is now mature, and is enabled by
  default. Complete UI support is coming in the next release. Hooks for
  message interception and manipulation are available.
* A myriad of other small improvements throughout the project.

## 16 October 2016: mitmproxy 0.18

* Python 3 Compatibility for mitmproxy and pathod (Shadab Zafar, GSoC 2016)
* Major improvements to mitmweb (Clemens Brunner & Jason Hao, GSoC 2016)
* Internal Core Refactor: Separation of most features into isolated Addons
* Initial Support for WebSockets
* Improved HTTP/2 Support
* Reverse Proxy Mode now automatically adjusts host headers and TLS Server Name Indication
* Improved HAR export
* Improved export functionality for curl, python code, raw http etc.
* Flow URLs are now truncated in the console for better visibility
* New filters for TCP, HTTP and marked flows.
* Mitmproxy now handles comma-separated Cookie headers
* Merge mitmproxy and pathod documentation
* Mitmdump now sanitizes its console output to not include control characters
* Improved message body handling for HTTP messages:
  `.raw_content` provides the message body as seen on the wire
  `.content` provides the decompressed body (e.g. un-gzipped)
  `.text` provides the body decompressed and decoded body
* New HTTP Message getters/setters for cookies and form contents.
* Add ability to view only marked flows in mitmproxy
* Improved Script Reloader (Always use polling, watch for whole directory)
* Use tox for testing
* Unicode support for tnetstrings
* Add dumpfile converters for mitmproxy versions 0.11 and 0.12
* Numerous bugfixes

## 9 April 2016: mitmproxy 0.17

* Simplify repository and release structure. mitmproxy now comes as a single package, including netlib and pathod.
* Rename the Python package from libmproxy to mitmproxy.
* New option to add server certs to client chain (CVE-2016-2402, John Kozyrakis)
* Enable HTTP/2 by default (Thomas Kriechbaumer)
* Improved HAR extractor (Shadab Zafar)
* Add icon for OSX and Windows binaries
* Add content view for query parameters (Will Coster)
* Initial work on Python 3 compatibility
* locust.io export (Zohar Lorberbaum)
* Fix XSS vulnerability in HTTP errors (Will Coster)
* Numerous bugfixes and minor improvements

## 15 February 2016: mitmproxy 0.16

* Completely revised HTTP2 implementation based on hyper-h2 (Thomas Kriechbaumer)
* Export flows as cURL command, Python code or raw HTTP (Shadab Zafar)
* Fixed compatibility with the Android Emulator (Will Coster)
* Script Reloader: Inline scripts are reloaded automatically if modified (Matthew Shao)
* Inline script hooks for TCP mode (Michael J. Bazzinotti)
* Add default ciphers to support iOS9 App Transport Security (Jorge Villacorta)
* Basic Authentication for mitmweb (Guillem Anguera)
* Exempt connections from interception based on TLS Server Name Indication (David Weinstein)
* Provide Python Wheels for faster installation
* Numerous bugfixes and minor improvements

## 4 December 2015: mitmproxy 0.15

* Support for loading and converting older dumpfile formats (0.13 and up)
* Content views for inline script (@chrisczub)
* Better handling of empty header values (Benjamin Lee/@bltb)
* Fix a gnarly memory leak in mitmdump
* A number of bugfixes and small improvements

## 6 November 2015: mitmproxy 0.14

* Statistics: 399 commits, 13 contributors, 79 closed issues, 37 closed
  PRs, 103 days
* Docs: Greatly updated docs now hosted on ReadTheDocs!
  http://docs.mitmproxy.org
* Docs: Fixed Typos, updated URLs etc. (Nick Badger, Ben Lerner, Choongwoo
  Han, onlywade, Jurriaan Bremer)
* mitmdump: Colorized TTY output
* mitmdump: Use mitmproxy's content views for human-readable output (Chris
  Czub)
* mitmproxy and mitmdump: Support for displaying UTF8 contents
* mitmproxy: add command line switch to disable mouse interaction (Timothy
  Elliott)
* mitmproxy: bug fixes (Choongwoo Han, sethp-jive, FreeArtMan)
* mitmweb: bug fixes (Colin Bendell)
* libmproxy: Add ability to fall back to TCP passthrough for non-HTTP
  connections.
* libmproxy: Avoid double-connect in case of TLS Server Name Indication.
  This yields a massive speedup for TLS handshakes.
* libmproxy: Prevent unnecessary upstream connections (macmantrl)
* Inline Scripts: New API for HTTP Headers:
  http://docs.mitmproxy.org/en/latest/dev/models.html#netlib.http.Headers
* Inline Scripts: Properly handle exceptions in `done` hook
* Inline Scripts: Allow relative imports, provide `__file__`
* Examples: Add probabilistic TLS passthrough as an inline script
* netlib: Refactored HTTP protocol handling code
* netlib: ALPN support
* netlib: fixed a bug in the optional certificate verification.
* netlib: Initial Python 3.5 support (this is the first prerequisite for
  3.x support in mitmproxy)

## 24 July 2015: mitmproxy 0.13

* Upstream certificate validation. See the --verify-upstream-cert,
  --upstream-trusted-confdir and --upstream-trusted-ca parameters. Thanks to
  Kyle Morton (github.com/kyle-m) for his work on this.
* Add HTTP transparent proxy mode. This uses the host headers from HTTP
  traffic (rather than SNI and IP address information from the OS) to
  implement perform transparent proxying. Thanks to github.com/ijiro123 for
  this feature.
* Add ~src and ~dst REGEX filters, allowing matching on source and
  destination addresses in the form of <IP>:<Port>
* mitmproxy console: change g/G keyboard shortcuts to match less. Thanks to
  Jose Luis Honorato (github.com/jlhonora).
* mitmproxy console: Flow marking and unmarking. Marked flows are not
  deleted when the flow list is cleared. Thanks to Jake Drahos
  (github.com/drahosj).
* mitmproxy console: add marking of flows
* Remove the certforward feature. It was added to allow exploitation of
  #gotofail, which is no longer a common vulnerability. Permitting this
  hugely increased the complexity of packaging and distributing mitmproxy.

## 3 June 2015: mitmproxy 0.12.1

* mitmproxy console: mouse interaction - scroll in the flow list, click on
  flow to view, click to switch between tabs.
* Update our crypto defaults: SHA256, 2048 bit RSA, 4096 bit DH parameters.
* BUGFIX: crash under some circumstances when copying to clipboard.
* BUGFIX: occasional crash when deleting flows.

## 18 May 2015: mitmproxy 0.12

* mitmproxy console: Significant revamp of the UI. The major changes are
  listed below, and in addition almost every aspect of the UI has
  been tweaked, and performance has improved significantly.
* mitmproxy console: A new options screen has been created ("o" shortcut),
  and many options that were previously manipulated directly via a
  keybinding have been moved there.
* mitmproxy console: Big improvement in palettes. This includes improvements
  to all colour schemes. Palettes now set the terminal background colour by
  default, and a new --palette-transparent option has been added to disable
  this.
* mitmproxy console: g/G shortcuts throughout mitmproxy console to jump
  to the beginning/end of the current view.
* mitmproxy console: switch  palettes on the fly from the options screen.
* mitmproxy console: A cookie editor has been added for mitmproxy console
  at long last.
* mitmproxy console: Various components of requests and responses can be
  copied to the clipboard from mitmproxy - thanks to @marceloglezer.
* Support for creating new requests from scratch in mitmproxy console (@marceloglezer).
* SSLKEYLOGFILE environment variable to specify a logging location for TLS
  master keys. This can be used with tools like Wireshark to allow TLS
  decoding.
* Server facing SSL cipher suite specification (thanks to Jim Shaver).
* Official support for transparent proxying on FreeBSD - thanks to Mike C
  (http://github.com/mike-pt).
* Many other small bugfixes and improvemenets throughout the project.

## 29 Dec 2014: mitmproxy 0.11.2

* Configuration files - mitmproxy.conf, mitmdump.conf, common.conf in the
  .mitmproxy directory.
* Better handling of servers that reject connections that are not SNI.
* Many other small bugfixes and improvements.

## 15 November 2014: mitmproxy 0.11.1

* Bug fixes: connection leaks some crashes

## 7 November 2014: mitmproxy 0.11

* Performance improvements for mitmproxy console
* SOCKS5 proxy mode allows mitmproxy to act as a SOCKS5 proxy server
* Data streaming for response bodies exceeding a threshold
  (bradpeabody@gmail.com)
* Ignore hosts or IP addresses, forwarding both HTTP and HTTPS traffic
  untouched
* Finer-grained control of traffic replay, including options to ignore
  contents or parameters when matching flows (marcelo.glezer@gmail.com)
* Pass arguments to inline scripts
* Configurable size limit on HTTP request and response bodies
* Per-domain specification of interception certificates and keys (see
  --cert option)
* Certificate forwarding, relaying upstream SSL certificates verbatim (see
  --cert-forward)
* Search and highlighting for HTTP request and response bodies in
  mitmproxy console (pedro@worcel.com)
* Transparent proxy support on Windows
* Improved error messages and logging
* Support for FreeBSD in transparent mode, using pf (zbrdge@gmail.com)
* Content view mode for WBXML (davidshaw835@air-watch.com)
* Better documentation, with a new section on proxy modes
* Generic TCP proxy mode
* Countless bugfixes and other small improvements
* pathod: Hugely improved SSL support, including dynamic generation of certificates
  using the mitproxy cacert

## 7 November 2014: pathod 0.11

* Hugely improved SSL support, including dynamic generation of certificates
  using the mitproxy cacert
* pathoc -S dumps information on the remote SSL certificate chain
* Big improvements to fuzzing, including random spec selection and memoization to avoid repeating randomly generated patterns
* Reflected patterns, allowing you to embed a pathod server response specification in a pathoc request, resolving both on client side. This makes fuzzing proxies and other intermediate systems much better.

## 28 January 2014: mitmproxy 0.10

* Support for multiple scripts and multiple script arguments
* Easy certificate install through the in-proxy web app, which is now
  enabled by default
* Forward proxy mode, that forwards proxy requests to an upstream HTTP server
* Reverse proxy now works with SSL
* Search within a request/response using the "/" and "n" shortcut keys
* A view that beatifies CSS files if cssutils is available
* Bug fix, documentation improvements, and more.

## 25 August 2013: mitmproxy 0.9.2

* Improvements to the mitmproxywrapper.py helper script for OSX.
* Don't take minor version into account when checking for serialized file
  compatibility.
* Fix a bug causing resource exhaustion under some circumstances for SSL
  connections.
* Revamp the way we store interception certificates. We used to store these
  on disk, they're now in-memory. This fixes a race condition related to
  cert handling, and improves compatibility with Windows, where the rules
  governing permitted file names are weird, resulting in errors for some
  valid IDNA-encoded names.
* Display transfer rates for responses in the flow list.
* Many other small bugfixes and improvements.

## 25 August 2013: pathod 0.9.2

* Adapt to interface changes in netlib

## 16 June 2013: mitmproxy 0.9.1

* Use "correct" case for Content-Type headers added by mitmproxy.
* Make UTF environment detection more robust.
* Improved MIME-type detection for viewers.
* Always read files in binary mode (Windows compatibility fix).
* Some developer documentation.

## 15 May 2013: mitmproxy 0.9

* Upstream certs mode is now the default.
* Add a WSGI container that lets you host in-proxy web applications.
* Full transparent proxy support for Linux and OSX.
* Introduce netlib, a common codebase for mitmproxy and pathod
  (http://github.com/cortesi/netlib).
* Full support for SNI.
* Color palettes for mitmproxy, tailored for light and dark terminal
  backgrounds.
* Stream flows to file as responses arrive with the "W" shortcut in
  mitmproxy.
* Extend the filter language, including ~d domain match operator, ~a to
  match asset flows (js, images, css).
* Follow mode in mitmproxy ("F" shortcut) to "tail" flows as they arrive.
* --dummy-certs option to specify and preserve the dummy certificate
  directory.
* Server replay from the current captured buffer.
* Huge improvements in content views. We now have viewers for AMF, HTML,
  JSON, Javascript, images, XML, URL-encoded forms, as well as hexadecimal
  and raw views.
* Add Set Headers, analogous to replacement hooks. Defines headers that are set
  on flows, based on a matching pattern.
* A graphical editor for path components in mitmproxy.
* A small set of standard user-agent strings, which can be used easily in
  the header editor.
* Proxy authentication to limit access to mitmproxy
* pathod: Proxy mode. You can now configure clients to use pathod as an
  HTTP/S proxy.
* pathoc: Proxy support, including using CONNECT to tunnel directly to
  targets.
* pathoc: client certificate support.
* pathod: API improvements, bugfixes.

## 15 May 2013: pathod 0.9 (version synced with mitmproxy)

* Pathod proxy mode. You can now configure clients to use pathod as an
  HTTP/S proxy.
* Pathoc proxy support, including using CONNECT to tunnel directly to
  targets.
* Pathoc client certificate support.
* API improvements, bugfixes.

## 16 November 2012: pathod 0.3

A release focusing on shoring up our fuzzing capabilities, especially with
pathoc.

* pathoc -q and -r options, output full request and response text.
* pathod -q and -r options, add full request and response text to pathod's
  log buffer.
* pathoc and pathod -x option, makes -q and -r options log in hex dump
  format.
* pathoc -C option, specify response codes to ignore.
* pathoc -T option, instructs pathoc to ignore timeouts.
* pathoc -o option, a one-shot mode that exits after the first non-ignored
  response.
* pathoc and pathod -e option, which explains the resulting message by
  expanding random and generated portions, and logging a reproducible
  specification.
* Streamline the specification language. HTTP response message is now
  specified using the "r" mnemonic.
* Add a "u" mnemonic for specifying User-Agent strings. Add a set of
  standard user-agent strings accessible through shortcuts.
* Major internal refactoring and cleanup.
* Many bugfixes.

## 22 August 2012: pathod 0.2

* Add pathoc, a pathological HTTP client.
* Add libpathod.test, a truss for using pathod in unit tests.
* Add an injection operator to the specification language.
* Allow Python escape sequences in value literals.
* Allow execution of requests and responses from file, using the new + operator.
* Add daemonization to Pathod, and make it more robust for public-facing use.
* Let pathod pick an arbitrary open port if -p 0 is specified.
* Move from Tornado to netlib, the network library written for mitmproxy.
* Move the web application to Flask.
* Massively expand the documentation.

## 5 April 2012: mitmproxy 0.8

* Detailed tutorial for Android interception. Some features that land in
  this release have finally made reliable Android interception possible.
* Upstream-cert mode, which uses information from the upstream server to
  generate interception certificates.
* Replacement patterns that let you easily do global replacements in flows
  matching filter patterns. Can be specified on the command-line, or edited
  interactively.
* Much more sophisticated and usable pretty printing of request bodies.
  Support for auto-indentation of Javascript, inspection of image EXIF
  data, and more.
* Details view for flows, showing connection and SSL cert information (X
  keyboard shortcut).
* Server certificates are now stored and serialized in saved traffic for
  later analysis. This means that the 0.8 serialization format is NOT
  compatible with 0.7.
* Many other improvements, including bugfixes, and expanded scripting API,
  and more sophisticated certificate handling.

## 20 February 2012: mitmproxy 0.7

* New built-in key/value editor. This lets you interactively edit URL query
  strings, headers and URL-encoded form data.
* Extend script API to allow duplication and replay of flows.
* API for easy manipulation of URL-encoded forms and query strings.
* Add "D" shortcut in mitmproxy to duplicate a flow.
* Reverse proxy mode. In this mode mitmproxy acts as an HTTP server,
  forwarding all traffic to a specified upstream server.
* UI improvements - use unicode characters to make GUI more compact,
  improve spacing and layout throughout.
* Add support for filtering by HTTP method.
* Add the ability to specify an HTTP body size limit.
* Move to typed netstrings for serialization format - this makes 0.7
  backwards-incompatible with serialized data from 0.6!

* Significant improvements in speed and responsiveness of UI.
* Many minor bugfixes and improvements.

## 7 August 2011: mitmproxy 0.6

* New scripting API that allows much more flexible and fine-grained
  rewriting of traffic. See the docs for more info.
* Support for gzip and deflate content encodings. A new "z"
  keybinding in mitmproxy to let us quickly encode and decode content, plus
  automatic decoding for the "pretty" view mode.
* An event log, viewable with the "v" shortcut in mitmproxy, and the
  "-e" command-line flag in mitmdump.
* Huge performance improvements: mitmproxy interface, loading
  large numbers of flows from file.
* A new "replace" convenience method for all flow objects, that does a
  universal regex-based string replacement.
* Header management has been rewritten to maintain both case and order.
* Improved stability for SSL interception.
* Default expiry time on generated SSL certs has been dropped to avoid an
  OpenSSL overflow bug that caused certificates to expire in the distant
  past on some systems.
* A "pretty" view mode for JSON and form submission data.
* Expanded documentation and examples.
* Countless other small improvements and bugfixes.

## 27 June 2011: mitmproxy 0.5

* An -n option to start the tools without binding to a proxy port.
* Allow scripts, hooks, sticky cookies etc. to run on flows loaded from
  save files.
* Regularize command-line options for mitmproxy and mitmdump.
* Add an "SSL exception" to mitmproxy's license to remove possible
  distribution issues.
* Add a --cert-wait-time option to make mitmproxy pause after a new SSL
  certificate is generated. This can pave over small discrepancies in
  system time between the client and server.
* Handle viewing big request and response bodies more elegantly. Only
  render the first 100k of large documents, and try to avoid running the
  XML indenter on non-XML data.
* BUGFIX: Make the "revert" keyboard shortcut in mitmproxy work after a
  flow has been replayed.
* BUGFIX: Repair a problem that sometimes caused SSL connections to consume
  100% of CPU.

## 30 March 2011: mitmproxy 0.4

* Full serialization of HTTP conversations
* Client and server replay
* On-the-fly generation of dummy SSL certificates
* mitmdump has "grown up" into a powerful tcpdump-like tool for HTTP/S
* Dozens of improvements to the mitmproxy console interface
* Python scripting hooks for programmatic modification of traffic

## 01 March 2010: mitmproxy 0.2

* Big speed and responsiveness improvements, thanks to Thomas Roth
* Support urwid 0.9.9
* Terminal beeping based on filter expressions
* Filter expressions for terminal beeps, limits, interceptions and sticky
  cookies can now be passed on the command line.
* Save requests and responses to file
* Split off non-interactive dump functionality into a new tool called
  mitmdump
* "A" will now accept all intercepted connections
* Lots of bugfixes
