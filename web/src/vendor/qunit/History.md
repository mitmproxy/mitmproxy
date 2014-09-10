1.15.0 / 2014-08-08
==================

* Assert: Implement Assert constructor with test context. This heavily improves debugging of async tests, since assertions can't leak into other tests anymore. Use the assert argument in your test callbacks to run assertions to get the full benefit of this.
* Assert: Improved the default message from assert.ok. Now assert.ok() outputs the exact value it received, instead of only saying it wasn't thruthy.
* Assert: Removal of raises, same and equals. These were deprecated a long time ago and finally removed. Use throws, deepEqual and equal instead.
* Core: Pass total amount of tests to QUnit.begin callback as totalTests. Will be used by Karma and other reporters.
* Dump: Move QUnit.jsDump to QUnit.dump. QUnit.jsDump still exists, but will be removed later. Use QUnit.dump.
* Dump: Output non-enumerable properties of TypeError. Makes it easier to compare properties of error objects.
* Reporter: Output only assertion count for green tests. Less visual clutter for passing tests.
* Reporter: Move HTML reporter to a new JS file. The HTML reporter is still bundled, but the code has been refactored to move it to a separate file.
* Test: Remove deprecated QUnit.current_testEnvironment
* Throws: support for oldIE native Error types. Error objects in IE are buggy, this works around those issues.

1.14.0 / 2014-01-31
==================

  * Grunt: Run tests on ios browserSet as well
  * Package: Set main property to qunit/qunit.js
  * Grunt: Inline browserSet config for TestSwarm runs
  * CSS: Removing redundancy
  * Core: Add config property for disabling default scroll-to-top
  * Grunt: Remove addons leftovers
  * Addons: Remove last remnants
  * Core: Extend QUnit.config.urlConfig to support select-one dropdowns
  * Assert: Extend throws to accept Error instances
  * Assert: Extend throws to handle errors as strings
  * CSS: Updating qunit.css for consistency
  * Core: Cache window.clearTimeout in case it gets mocked
  * Core: Run multiple tests by test number
  * jshint: add es3 option to ensure oldie support

1.13.0 / 2014-01-04
==================

  * Tests: Stop using the expected argument in test() calls
  * Logging: Add runtime property to testDone, deprecate duration
  * Assert: Remove raises (deprecated 2012), replace with failed assertion
  * Grunt: Add non-browser test as grunt task. Runs existing tests in node.
  * Export: Only export to the variable that we check for.
  * Core: Properly check for existence of document
  * Core: Remove triggerEvent, which isn't used or documented anywhere.
  * Core: Silence addEvent in non-browser env
  * The Grand QUnit Split of 2013
  * Use `id` function for selection elements in two places that were not using it. Closes gh-463
  * Add bower.json. Fixes #461

1.12.0 / 2013-06-21
===================

  * Add a deprecation comment to QUnit.reset. Partial fix for #354
  * Fix mis-match between moduleStart and moduleDone events
  * Removed jQuery.trim optimization. Fixes #424.
  * Use a local setTimeout reference, add separate unit test suite for that. Fixes #432 - Using a setTimeout stub can stop test suite from continuing. Closes gh-433
  * Added CONTRIBUTING.md.
  * Moved 'addons/themes/nv' to 'Krinkle/qunit-theme-nv.git'
  * Moved 'addons/themes/ninja' to 'Krinkle/qunit-theme-ninja.git'
  * Moved 'addons/themes/gabe' to 'Krinkle/qunit-theme-gabe.git'
  * Moved 'addons/canvas' to 'JamesMGreene/qunit-assert-canvas.git'. Tree: https://github.com/JamesMGreene/qunit-assert-canvas/tree/v1.0.0
  * Moved 'addons/close-enough' to 'JamesMGreene/qunit-assert-close.git'. Tree: https://github.com/JamesMGreene/qunit-assert-close/tree/v1.0.0
  * Moved 'addons/step' to 'JamesMGreene/qunit-assert-step.git'. Tree: https://github.com/JamesMGreene/qunit-assert-step/tree/v1.0.0
  * Canvas plugin: Show how to test with images. Closes gh-438.
  * Clear filter and testNumber when choosing a module. Fixes #442.
  * Deprecate QUnit.current_testEnvironment in favour of config.current.testEnvironment.
  * assert.ok: Message shouldn't be undefined in 'log' event.
  * Emit moduleStart before testStart even if test isn't in a module.
  * PhantomJS plugin: Added optional timeout. Closes #415.
  * PhantomJS plugin: Include stack trace for all failed tests. Closes #416.
  * Moved 'addons/composite' to 'jquery/qunit-composite.git'. Tree: https://github.com/jquery/qunit-composite/tree/v1.0.0 Fixes #419.
  * Moved 'addons/junitlogger' to 'jquery/qunit-reporter-junit.git'.
  * Sort the module names so we no longer rely on implicit ordering. Fixes #391. Closes gh-392
  * JUnitLogger: Add a `name` property to the test run. Closes gh-389
  * Improve circular reference logic in equiv - Fixes #397

1.11.0 / 2013-01-20
==================

  * Diff: Fix exception on property "constructor". Fixes #394.
  * Composite Add-on: Test suites can be named by including an obj with name & path props within array param for .testSuites()
  * Fix URL generator to take protocol and host into account to fix usage with file protocol in IE7/8
  * Fix issue with Error.prototype.toString in IE 7
  * Refactor jsDump for "node". Fixes #381.
  * Show contents of text nodes in jsDump.node. Fixes #380.
  * Escape text. Fixes #379.
  * Rewrote most of the JUnitLogger addon as it was in bad shape: unused variables, duplicate effort that QUnit handles internally (e.g. tallying number of total assertions, failed assertions, etc.), sub-optimal XmlWriter implementation, etc.
  * Phantomjs: Include source in assertion details
  * Phantomjs: Removed the polling mechanism in favor of PhantomJS 1.6+'s `WebPage#onCallback`
  * Delay start() until init() happened. Fixes #358. Closes #373.
  * urlConfig: Fix checkbox event for oldIE. Fixes #369. Closes #370.
  * Issue #365: Fix module picker for oldIE. Closes #366.
  * Fixes #344 - Capture and show test duration.
  * Rename tests to assertions in summary. Fixes #336 - Summary counts assertions but mentions 'tests'.
  * Assert: Implement propEqual and notPropEqual. Fixes #317.
  * Canvas addon: Use 0.6 as alpha value to avoid inconsistencies between browsers. Fixes #342
  * Remove global variable "assert". Fixes #341.
  * Add a test for loading tests asynchronously
  * Improve start()-called-too-often fix, initialize semaphore at 1, fixes autostart=false case. Also provide stack for the offending start() call
  * There's type-free objects in Firefox, extend objectType() to allow null match. Fixes #315
  * Push a failing assertion when calling start() while already running. Resets anyway to keep other tests going. Fixes #314
  * Adds Ninja Theme
  * Extend jsdump to output Error objects as such, including the message property. Extend throws to provide 'expected' value when possible. Fixes #307
  * Use classes to collapse assertion groups. Fixes #269
  * Readme for junitlogger addon
  * Better readme for composite addon
  * Make `throws` ES3 compatible
  * Composite: Adds test whether iframe contains content. Fixes #318 - Composite: Raises "global failure" in Opera
  * Apply the same exception handling for test and teardown try/catch as for setup

1.10.0 / 2012-08-30
==================

  * Simplify licensing: Only MIT, no more MIT/GPL dual licensing.
  * Scroll the window back to top after tests finished running. Fixes #304
  * Simplify phantomjs runner to use module property in testDone callback
  * Adds module and test name to the information that is returned in the callback provided to QUnit.log(Function). Fixes #296
  * Make QUnit.expect() (without arguments) a getter. Fixes #226
  * Compare the ES6 sticky (y) property for RegExp. Can't add to tests yet. Fixes #284 - deepEqual for RegExp should compare
  * onerror: force display of global errors despite URL parameters. Fixes #288 - Global failures can be filtered out by test-limiting URL parameters
  * Remove conditional codepath based on jQuery presence from reset().
  * Add module filter to UI
  * Keep a local reference to Date. Fixes #283.
  * Update copyright to jQuery Foundation.

1.9.0 / 2012-07-11
==================
  * added jsdoc for QUnit.assert functions
  * Styling: radius to 5px and small pass/error border, remove inner shadow
  * Move checkboxes into toolbar and give them labels and descriptions (as tooltip). Fixes #274 - Improve urlFilter API and UI
  * Where we receive no exception in throws() use a relevant message.
  * Also make module filter case-insensitive. Follow-up to #252
  * Banner: Link should ignore "testNumber" and "module". Fixes #270
  * Rename assert.raises to assert.throws. Fixes #267
  * Change package.json name property to 'qunitjs' to avoid conflict with node-qunit; will publish next release to npm

1.8.0 / 2012-06-14
==================
  * Improve window.onerror handling
  * (issue #260) config.current should be reset at the right time.
  * Filter: Implement 'module' url parameter. Fixes #252
  * raises: ignore global exceptions stemming from test. Fixes #257 - Globally-executed errors sneak past raises in IE

1.7.0 / 2012-06-07
==================

  * Add config.requireExpects. Fixes #207 - Add option to require all tests to call expect().
  * Improve extractStacktrace() implementation. Fixes #254 - Include all relevant stack lines
  * Make filters case-insensitive. Partial fix for #252
  * is() expects lowercase types. Fixes #250 - Expected Date value is not displayed properly
  * Fix phantomjs addon header and add readme. Fixes #239
  * Add some hints to composite addon readme. Fixes #251
  * Track tests by the order in which they were run and create rerun links based on that number. Fixes #241 - Make Rerun link run only a single test.
  * Use QUnit.push for raises implementation. Fixes #243
  * CLI runner for phantomjs
  * Fix jshint validation until they deal with /** */ comments properly
  * Update validTest() : Simplify logic, clarify vars and add comments
  * Refactor assertion helpers into QUnit.assert (backwards compatible)
  * Add Rerun link to placeholders. Fixes #240

1.6.0 / 2012-05-04
==================

  * Save stack for each test, use that for failed expect() results, points at the line where test() was called. Fixes #209
  * Prefix test-output id and ignore that in noglobals check. Fixes #212
  * Only check for an exports object to detect a CommonJS environment. Fixes #237 - Incompatibility with require.js
  * Add testswarm integration as grunt task
  * Added padding on URL config checkboxes.
  * Cleanup composite addon: Use callback registration instead of overwriting them. Set the correct src on rerun link (and dblclick). Remove the composite test itself, as that was a crazy hack not worth maintaining
  * Cleanup reset() test and usage - run testDone callback first, to allow listeneres ignoring reset assertions
  * Double clicking on composite test rows opens individual test page
  * test-message for all message-bearing API reporting details

1.5.0 / 2012-04-04
==================

  * Modify "Running..." to display test name. Fixes #220
  * Fixed clearing of sessionStorage in Firefox 3.6.
  * Fixes #217 by calling "block" with config.current.testEnvironment
  * Add stats results to data. QUnit.jUnitReport function take one argument {   xml:'<?xml ...',   results:{failed:0, passed:0, total:0, time:0} }
  * Add link to MDN about stack property

1.4.0 / 2012-03-10
==================

  * Prefix test-related session-storage items to make removal more specific. Fixes #213 - Keep hide-passed state when clearing session storage
  * Update grunt.js with separate configs for qunit.js and grunt.js, also add tests but disable for now, not passing yet. Add grunt to devDependencies
  * typo
  * Cleanup grunt.js, no need for the banner
  * Fix lint errors and some formatting issues. Use QUnit.pushFailure for noglobals and global error handler.
  * Fix a missing expect in logs test
  * Add grunt.js configuration and include some usage instructions in the readme
  * Update package.json
  * Partially revert af27eae841c3e1c01c46de72d676f1047e1ee375 - can't move reset around, so also don't wrap in try-catch, as the result of that is effectively swallowed. Can't output the result as the outputting is already done.
  * Add QUnit.pushFailure to log error conditions like exceptions. Accepts stacktrace as second argument, allowing extraction with catched exceptions (useful even in Safari). Remove old fail() function that would just log to console, not useful anymore as regular test output is much more useful by now. Move up QUnit.reset() call to just make that another failed assertion. Used to not make a test fail. Fixes #210
  * Update equals and same deprecations to use QUnit.push to provide correct source lines. Fixes #211
  * Add a test file for narwhal integration. Has to use print instead of console.log. Fails when an assertion fails, something about setInterval...
  * Apply notrycatch option to setup and teardown as well. Fixes #203. Reorder noglobals check to allow teardown to remove globals that were introduced intentionally. Fixes #204
  * Extend exports object with QUnit properties at the end of the file to export everything.
  * Output source line for ok() assertions. Fixes #202
  * Make test fail if no assertions run. Fixes #178
  * Sort object output alphabetically in order to improve diffs of objects where properties were set in a different order. Fixes #206
  * Revert "Change fixture reset behavior", changing #194 and #195 to wontfix.

1.3.0 / 2012-02-26
==================

  * Cleanup test markup
  * Fix the jQuery branch of fixture reset. Would break when no fixture exists.
  * Added initial version of a junitlogger addon.
  * Escape document.title before inserting into markup. Extends fix for #127
  * Catch assertions running outside of test() context, make sure source is provided even for ok(). Fixes #98
  * Improve global object access, based on comments for 1a9120651d5464773256d8a1f2cf2eabe38ea5b3
  * Clear all sessionStorage entries once all tests passed. Helps getting rid of items from renamed tests. Fixes #101
  * Set fixed dimensions for #qunit-fixture. Fixes #114
  * Extend nodejs test runner to check for stacktrace output, twice
  * Extend nodejs test runner to check for stacktrace output
  * Generate more base markup, but allow the user to exclude that completely or choose their own. Fixes #127
  * Add a simple test file to check basic nodejs integration works
  * Check for global object to find setTimeout in node
  * Fix CommonJS export by assigning QUnit to module.exports.
  * Remove the testEnvironmentArg to test(). Most obscure, never used anywhere. test() is still heavily overloaded with argument shifting, this makes it a little more sane. Fixes #172
  * Serialize expected and actual values only when test fails. Speeds up output of valid tests, especially for lots of large objects. Fixes #183
  * Fix sourceFromsTacktrace to get the right line in Firefox. Shift the 'error' line away in Chrome to get a match.
  * Fix references to test/deepEqual.js
  * In autorun mode, moduleDone is called without matching moduleStart. Fix issue #184
  * Fixture test: allow anything falsy in test as getAttribute in oldIE will return empty string instead of null. We don't really care.
  * Keep label and checkbox together ( http://i.imgur.com/5Wk3A.png )
  * Add readme for themes
  * Fix bad global in reset()
  * Some cleanup in theme addons
  * Update headers
  * Update nv.html, add gabe theme based on https://github.com/jquery/qunit/pull/188
  * Experimental custom theme based on https://github.com/jquery/qunit/pull/62 by NV
  * Replace deprecated same and equals aliases with placeholders that just throw errors, providing a hint at what to use instead. Rename test file to match that.
  * Can't rely on outerHTML for Firefox < 11. Use cloneNode instead.
  * Merge remote branch 'conzett/master'
  * Cleanup whitespace
  * Update sessionStorage support test to latest version from Modernizr, trying to setItem to avoid QUOTA_EXCEEDED_EXCEPTION
  * Change fixture reset behavior
  * Merge pull request #181 from simonz/development
  * Escaping test names
  * Show exception stack when test failed

1.2.0 / 2011-11-24
==================

  * remove uses of equals(), as it's deprecated in favor of equal()
  * Code review of "Allow objects with no prototype to be tested against object literals."
  * Allow objects with no prototype to tested against object literals.
  * Fix IE8 "Member not found" error
  * Using node-qunit port, the start/stop function are not exposed so we need to prefix any call to them with 'QUnit'. Aka: start() -> QUnit.start()
  * Remove the 'let teardown clean up globals test' - IE<9 doesn't support (==buggy) deleting window properties, and that's not worth the trouble, as everything else passes just fine. Fixes #155
  * Fix globals in test.js, part 2
  * Fix globals in test.js. ?tell wwalser to use ?noglobals everyonce in a while
  * Extend readme regarding release process

1.1.0 / 2011-10-11
==================

  * Fixes #134 - Add a window.onerror handler. Makes uncaught errors actually fail the testsuite, instead of going by unnoticed.
  * Whitespace cleanup
  * Merge remote branch 'trevorparscal/master'
  * Fixed IE compatibility issues with using toString on NodeList objects, which in some browsers results in [object Object] rather than [object NodeList]. Now using duck typing for NodeList objects based on the presence of length, length being a number, presence of item method (which will be typeof string in IE and function in others, so we just check that it's not undefined) and that item(0) returns the same value as [0], unless it's empty, in which case item(0) will return 0, while [0] would return undefined. Tested in IE6, IE8, Firefox 6, Safari 5 and Chrome 16.
  * Update readme with basic notes on releases
  * More whitespace/parens cleanup
  * Check if setTimeout is available before trying to delay running the next task. Fixes #160
  * Whitespace/formatting fix, remove unnecessary parens
  * Use alias for Object.prototype.toString
  * Merge remote branch 'trevorparscal/master'
  * Merge remote branch 'wwalser/recursionBug'
  * Default 'expected' to null in asyncTest(), same as in test() itself.
  * Whitespace cleanup
  * Merge remote branch 'mmchaney/master'
  * Merge remote branch 'Krinkle/master'
  * Using === instead of ==
  * Added more strict array type detection for dump output, and allowed NodeList objects to be output as arrays
  * Fixes a bug where after an async test, assertions could move between test cases because of internal state (config.current) being incorrectly set
  * Simplified check for assertion count and adjusted whitespace
  * Redo of fixing issue #156 (Support Object.prototype extending environment). * QUnit.diff: Throws exception without this if Object.prototype is set (Property 'length' of undefined. Since Object.prototype.foo doesn't have a property 'rows') * QUnit.url: Without this fix, if Object.prototype.foo is set, the url will be set to ?foo=...&the=rest. * saveGlobals: Without this fix, whenever a member is added to Object.prototype, saveGlobals will think it was a global variable in this loop. --- This time using the call method instead of obj.hasOwnProperty(key), which may fail if the object has that as it's own property (touché!).
  * Handle expect(0) as expected, i.e. expect(0); ok(true, foo); will cause a test to fail

1.0.0 / 2011-10-06
==================

  * Make QUnit work with TestSwarm
  * Run other addons tests as composite addon demo. Need to move that to /test folder once this setup actually works
  * Add-on: New assertion-type: step()
  * added parameter to start and stop allowing a user to increment/decrement the semaphore more than once per call
  * Update readmes with .md extension for GitHub to render them as markdown
  * Update close-enough addon to include readme and match (new) naming conventions
  * Merge remote branch 'righi/close-enough-addon'
  * Canvas addon: Update file references
  * Update canvas addon: Rename files and add README
  * Merge remote branch 'wwalser/composite'
  * Fix #142 - Backslash characters in messages should not be escaped
  * Add module name to testStart and testDone callbacks
  * Removed extra columns in object literals. Closes #153
  * Remove dead links in comments.
  * Merge remote branch 'wwalser/multipleCallbacks'
  * Fixed syntax error and CommonJS incompatibilities in package.json
  * Allow multiple callbacks to be registered.
  * Add placeholder for when Safari may end up providing useful error handling
  * changed file names to match addon naming convention
  * Whitespace
  * Created the composite addon.
  * Using array and object literals.
  * Issue #140: Make toggle system configurable.
  * Merge remote branch 'tweetdeck/master'
  * Adds the 'close enough' addon to determine if numbers are acceptably close enough in value.
  * Fix recursion support in jsDump, along with tests. Fixes #63 and #100
  * Adding a QUnit.config.altertitle flag which will allow users to opt-out of the functionality introduced in 60147ca0164e3d810b8a9bf46981c3d9cc569efc
  * Refactor window.load handler into QUnit.load, makes it possible to call it manually.
  * More whitespace cleanup
  * Merge remote branch 'erikvold/one-chk-in-title'
  * Whitespace
  * Merge remote branch 'wwalser/syncStopCalls'
  * Introducing the first QUnit addon, based on https://github.com/jquery/qunit/pull/84 - adds QUnit.pixelEqual assertion method, along with example tests.
  * Remove config.hidepassed setting in test.js, wasn't intended to land in master.
  * Expose QUnit.config.hidepassed setting. Overrides sessionStorage and enables enabling the feature programmatically. Fixes #133
  * Fix formatting (css whitespace) for tracebacks.
  * Expose extend, id, and addEvent methods.
  * minor comment typo correction
  * Ignore Eclipse WTP .settings
  * Set 'The jQuery Project' as author in package.json
  * Fixes a bug where synchronous calls to stop would cause tests to end before start was called again
  * Point to planning testing wiki in readme
  * only add one checkmark to the document.title
  * Escape the stacktrace output before setting it as innerHTML, since it tends to contain `<` and `>` characters.
  * Cleanup whitespace
  * Run module.teardown before checking for pollution. Fixes #109 - noglobals should run after module teardown
  * Fix accidental global variable "not"
  * Update document.title status to use more robust unicode escape sequences, works even when served with non-utf-8-charset.
  * Modify document.title when suite is done to show success/failure in tab, allows you to see the overall result without seeing the tab content.
  * Merge pull request #107 from sexyprout/master
  * Set a generic font
  * Add/update headers
  * Drop support for deprecated #main in favor of #qunit-fixture. If this breaks your testsuite, replace id="main" with id="qunit-fixture". Fixes #103
  * Remove the same key as the one being set. Partial fix for #101
  * Don't modify expected-count when checking pollution. The failing assertion isn't expected, so shouldn't be counted. And if expect wasn't used, the count is misleading.
  * Fix order of noglobals check to produce correct introduced/delete error messages
  * Prepend module name to sessionStorage keys to avoid conflicts
  * Store filter-tests only when checked
  * Write to sessionStorage only bad tests
  * Moved QUnit.url() definition after QUnit properties are merged into the global scope. Fixes #93 - QUnit url/extend function breaking urls in jQuery ajax test component
  * Add a "Rerun" link to each test to replace the dblclick (still supported, for now).
  * Fixed the regex for parsing the name of a test when double clicking to filter.
  * Merge remote branch 'scottgonzalez/url'
  * Added checkboxes to show which flags are currently on and allow toggling them.
  * Retain all querystring parameters when filtering a test via double click.
  * Added better querystring parsing. Now storing all querystring params in QUnit.urlParams so that we can carry the params forward when filtering to a specific test. This removes the ability to specify multiple filters.
  * Make reordering optional (QUnit.config.reorder = false) and optimize "Hide passed tests" mode by also hiding "Running [testname]" entries.
  * Added missing semicolons and wrapped undefined key in quotes.
  * Optimize test hiding, add class on page load if stored in sessionStorage
  * Optimize the hiding of passed tests.
  * Position test results above test list, making it visible without ever having to scroll. Create a placeholder to avoid pushing down results later.
  * Don't check for existing qunit-testresult element, it gets killed on init anyway.
  * Added URL flag ?notrycatch (ala ?noglobals) for debugging exceptions. Won't try/catch test code, giving better debugging changes on the original exceptions. Fixes #72
  * Always show qunit-toolbar (if at all specified), persist checkbox via sessionStorage. Fixes #47
  * Use non-html testname for calls to fail(). Fixes #77
  * Overhaul of QUnit.callbacks. Consistent single argument with related properties, with additional runtime property for QUnit.done
  * Extended test/logs.html to capture more of the callbacks.
  * Fixed moduleStart/Done callbacks. Added test/logs.html to test these callbacks. To be extended.
  * Update copyright and license header. Fixes #61
  * Formatting fix.
  * Use a semaphore to synchronize stop() and start() calls. Fixes #76
  * Merge branch 'master' of https://github.com/paulirish/qunit into paulirish-master
  * Added two tests for previous QUnit.raises behaviour. For #69
  * add optional 2. arg to QUnit.raises #69.
  * fix references inside Complex Instances Nesting to what was originally intended.
  * Qualify calls to ok() in raises() for compatibility with CLI environments.
  * Fix done() handling, check for blocking, not block property
  * Fix moduleStart/Done and done callbacks.
  * Replacing sessionStorage test with the one from Modernizr/master (instead of current release). Here's hoping it'll work for some time.
  * Updated test for availability of sessionStorage, based on test from Modernizr. Fixes #64
  * Defer test execution when previous run passed, persisted via sessionStorage. Fixes #49
  * Refactored module handling and queuing to enable selective defer of test runs.
  * Move assertions property from config to Test
  * Move expected-tests property from config to Test
  * Refactored test() method to delegate to a Test object to encapsulate all properties and methods of a single test, allowing further modifications.
  * Adding output of sourcefile and linenumber of failed assertions (except ok()). Only limited cross-browser support for now. Fixes #60
  * Drop 'hide missing tests' feature. Fixes #48
  * Adding readme. Fixes #58
  * Merge branch 'prettydiff'
  * Improve jsDump output with formatted diffs.
  * Cleanup whitespace
  * Cleanup whitespace
  * Added additional guards around browser specific code and cleaned up jsDump code
  * Added guards around tests which are only for browsers
  * cleaned up setTimeout undefined checking and double done on test finish
  * fixing .gitignore
  * making window setTimeout query more consistent
  * Moved expect-code back to beginning of function, where it belongs. Fixes #52
  * Bread crumb in header: Link to suite without filters, add link to current page based on the filter, if present. Fixes #50
  * Make the toolbar element optional when checking for show/hide of test results. Fixes #46
  * Adding headless.html to manually test logging and verify that QUnit works without output elements. Keeping #qunit-fixture as a few tests actually use that.
  * Fix for QUnit.moduleDone, get rid of initial bogus log. Fixes #33
  * Pass raw data (result, message, actual, expected) as third argument to QUnit.log. Fixes #32
  * Dump full exception. Not pretty, but functional (see issue Pretty diff for pretty output). Fixes #31
  * Don't let QUnit.reset() cause assertions to run. Manually applied from Scott Gonzalez branch. Fixes #34
  * Added missing semicolons. Fixes #37
  * Show okay/failed instead of undefined. Fixes #38
  * Expose push as QUnit.push to build custom assertions. Fixes #39
  * Respect filter pass selection when writing new results. Fixes #43
  * Cleanup tests, removing asyncTest-undefined check and formatting
  * Reset: Fall back to innerHTML when jQuery isn't available. Fixes #44
  * Merge branch 'master' of github.com:jquery/qunit
  * reset doesn't exist here - fixes #28.
  * - less css cruft, better readability - replaced inline style for test counts with "counts" class - test counts now use a "failed"/"passed" vs "pass"/"fail", shorter/more distinct selectors - pulled all test counts styling together and up (they're always the same regardless of section pass/fail state)
  * Adding .gitignore file
  * Removing diff test - diffing works fine, as the browser collapses whitespace in its output, but the test can't do that and isn't worth fixing.
  * Always synchronize the done-step (it'll set the timeout when necessary), fixes timing race conditions.
  * Insert location.href as an anchor around the header. Fixes issue #29
  * - kill double ;; in escapeHtml. oops
  * Removed html escaping from QUnit.diff, as input is already escaped, only leads to double escaping. Replaced newlines with single whitespace.
  * Optimized and cleaned up CSS file
  * Making the reset-method non-global (only module, test and assertions should be global), and fixing the fixture reset by using jQuery's html() method again, doesn't work with innerHTML, yet
  * Introducing #qunit-fixture element, deprecating the (never documented) #main element. Doesn't require inline styles and is now independent of jQuery.
  * Ammending previous commit: Remove jQuery-core specific resets (will be replaced within jQuery testsuite). Fixes issue #19 - QUnit.reset() removes global jQuery ajax event handlers
  * Remove jQuery-core specific resets (will be replaced within jQuery testsuite). Fixes issue #19 - QUnit.reset() removes global jQuery ajax event handlers
  * Cleaning up rubble from the previous commit.
  * Added raises assertion, reusing some of kensnyder's code.
  * Merged kensnyder's object detection code. Original message: Streamlined object detection and exposed QUnit.objectType as a function.
  * Fixed some bad formatting.
  * Move various QUnit properties below the globals-export to avoid init becoming a global method. Fixes issue #11 - Remove 'init' function from a global namespace
  * Improved output when expected != actual: Output both only then, and add a diff. Fixes issue #10 - Show diff if equal() or deepEqual() failed
  * Expand failed tests on load. Fixes issue #8 - Failed tests expanded on load
  * Set location.search for url-filtering instead of location.href. Fixes issue #7 - Modify location.search instead of location.href on test double-click
  * Add QUnit.begin() callback. Fixes issue #6 - Add 'start' callback.
  * add css style for result (".test-actual") in passed tests
  * Fixed output escaping by using leeoniya's custom escaping along with innerHTML. Also paves the way for outputting diffs.
  * Cleanup
  * Revert "Revert part of bad merge, back to using createTextNode"
  * Revert part of bad merge, back to using createTextNode
  * Fixed doubleclick-handler and filtering to rerun only a single test.
  * Add ability to css style a test's messages, expected and actual results. Merged from Leon Sorokin (leeoniya).
  * Remove space between module name and colon
  * - removed "module" wording from reports (unneeded and cluttery) - added and modified css to make module & test names styleable
  * Logging support for  Each test can extend the module testEnvironment
  * Fixing whitespace
  * Update tests to use equal() and deepEqual() rather than the deprecated equals() and same()
  * Consistent argument names for deepEqual
  * Skip DOM part of jsDump test if using a SSJS environment without a DOM
  * Improve async testing by creating the result element before running the test, updating it later. If the test fails, its clear which test is the culprit.
  * Add autostart option to config. Set via QUnit.config.autostart = false; start later via QUnit.start()
  * Expose QUnit.config, but don't make config a global
  * Expose QUnit.config as global to make external workarounds easier
  * Merge branch 'asyncsetup'
  * Allowing async setup and teardown. Fixes http://github.com/jquery/qunit/issues#issue/20
  * Always output expected and actual result (no reason not to). Fixes http://github.com/jquery/qunit/issues#issue/21
  * More changes to the detection of types in jsDump's typeOf.
  * Change the typeOf checks in QUnit to be more accurate.
  * Added test for jsDump and modified its options to properly output results when document.createTextNode is used; currently tests for DOM elements cause a stackoverflow error in IEs, works fine, with the correct output, elsewhere
  * Always use jsDump to output result objects into messages, making the output for passing assertions more useful
  * Make it so that the display is updated, at least, once a second - also prevents scripts from executing for too long and causing problems.
  * added tests and patch for qunit.equiv to avoid circular references in objects and arrays
  * No reason to continue looping, we can stop at this point. Thanks to Chris Thatcher for the suggestion.
  * Use createTextNode instead of innerHTML for showing test result since expected and actual might be something that looks like a tag.
  * 'Test card' design added
  * switched green to blue for top-level pass + reduced padding
  * Bringing the QUnit API in line with the CommonJS API.
  * Explicitly set list-style-position: inside on result LIs.
  * Madness with border-radius.
  * Corrected banner styles for new class names
  * Added rounded corners and removed body rules for embedded tests
  * Resolving merge conflicts.
  * added colouring for value summary
  * adding some extra text colours
  * added styles for toolbar
  * added new styles
  * IE 6 and 7 weren't respecting the CSS rules for the banner, used a different technique instead.
  * Went a bit further and made extra-sure that the target was specified correctly.
  * Fixed problem where double-clicking an entry in IE caused an error to occur.
  * Path for http://dev.jquery.com/ticket/5426 - fix the microformat test result
  * Fixed test() to use 'expected' 2nd param
  * Remove the named function expressions, to stop Safari 2 from freaking out. Fixes #5.
  * Each test can extend the module testEnvironment
  * Extra test for current test environment
  * Make the current testEnvironment available to utility functions
  * typeOf in QUnit.jsDump now uses QUnit.is
  * hoozit in QUnit.equiv now uses QUnit.is
  * Properly set label attributes.
  * Some minor tweaks to RyanS' GETParams change.
  * left a console.log in :(
  * Took into account a fringe case when using qunit with testswarm. Trying to run all the tests with the extra url params from testswarm would make qunit look for a testsuite that did not exist
  * need to set config.currentModule to have correct names and working filters
  * Support logging of testEnvironment
  * async tests aren't possible on rhino
  * Fixed a missing QUnit.reset().
  * The QUnit. prefix was missing from the uses of the start() method.
  * Merged lifecycle object into testEnvironment
  * "replacing totally wrong diff algorithm with a working one" Patch from kassens (manually applied).
  * fixing jslint errors in test.js
  * Fixed: testDone() was always called with 0 failures in CommonJS mode
  * Fixed: moduleDone() was invoked on first call to module()
  * Added a new asyncTest method - removes the need for having to call start() at the beginning of an asynchronous test.
  * Added support for expected numbers in the test method.
  * Fixed broken dynamic loading of tests (can now dynamically load tests and done still works properly).
  * Simplified the logic for calling 'done' and pushing off new tests - was causing too many inconsistencies otherwise.
  * Simplified the markup for the QUnit test test suite.
  * Realized that it's really easy to handle the case where stop() has been called and then an exception is thrown.
  * Added in better logging support. Now handle moduleStart/moduleDone and testStart/testDone. Also make sure that done only fires once at the end.
  * Made it so that you can reset the suite to an initial state (at which point tests can be dynamically loaded and run, for example).
  * Re-worked QUnit to handle dynamic loading of additional code (the 'done' code will be re-run after additional code is loaded).
  * Removed the old SVN version stuff.
  * Moved the QUnit source into a separate directory and updated the test suite/packages files.
  * Added in CommonJS support for exporting the QUnit functionality.
  * Missing quote from package.json.
  * Fixed trailing comma in package.json.
  * Added a CommonJS/Narwhal package.json file.
  * Accidentally reverted the jsDump/equiv changes that had been made.
  * Hide the filter toolbar if it's not needed. Also exposed the jsDump and equiv objects on QUnit.
  * Retooled the QUnit CSS to be more generic.
  * Renamed the QUnit files from testrunner/testsuite to QUnit.
  * Expose QUnit.equiv and QUnit.jsDump in QUnit.
  * Moved the QUnit test directory into the QUnit directory.
  * Reworked the QUnit CSS (moved jQuery-specific stuff out, made all the other selectors more specific).
  * Removed the #main reset for non-jQuery code (QUnit.reset can be overwritten with your own reset code).
  * Moved the QUnit toolbar inline.
  * Switched to using a qunit- prefix for special elements (banner, userAgent, and tests).
  * Missed a case in QUnit where an element was assumed to exist.
  * QUnit's isSet and isObj are no longer needed - you should use same instead.
  * Make sure that QUnit's equiv entity escaping is enabled by default (otherwise the output gets kind of crazy).
  * Refactored QUnit, completely reorganized the structure of the file. Additionally made it so that QUnit can run outside of a browser (inside Rhino, for example).
  * Removed some legacy and jQuery-specific test methods.
  * Added callbacks for tests and modules. It's now possible to reproduce the full display of the testrunner without using the regular rendering.
  * QUnit no longer depends upon rendering the results (it can work simply by using the logging callbacks).
  * Made QUnit no longer require jQuery (it is now a standalone, framework independent, test runner).
  * Reverted the noglobals changed from QUnit - causing chaos in the jQuery test suite.
  * qunit: removed noglobals flag, instead always check for globals after teardown; if a test has to introduce a global "myVar", use delete window.myVar in teardown or at the end of a test
  * qunit: don't child selectors when IE should behave nicely, too
  * qunit: improvement for the test-scope: create a new object and call setup, the test, and teardown in the scope of that object - allows you to provide test fixtures to each test without messing with global data; kudos to Martin Häcker for the contribution
  * qunit: added missing semicolons
  * qunit: fixed a semicolon, that should have been a comma
  * QUnit: implemented error handling for Opera as proposed by #3628
  * qunit: fix for http://dev.jquery.com/ticket/3215 changing wording of testresults, to something more positive (x of y passed, z failed)
  * QUnit: testrunner.js: Ensures equality of types (String, Boolean, Number) declared with the 'new' prefix. See comments #3, #4 and #5 on http://philrathe.com/articles/equiv
  * qunit: wrap name of test in span when a module is used for better styling
  * qunit: auto-prepend default mark (#header, #banner, #userAgent, #tests) when not present
  * Landing some changes to add logging to QUnit (so that it's easier to hook in to when a test finishes).
  * Added checkbox for hiding missing tests (tests that fail with the text 'missing test - untested code is broken code')
  * qunit: eol-style:native and mime-type
  * HTML being injected for the test result wasn't valid HTML.
  * qunit: setting mimetype for testsuite.css
  * qunit: update to Ariel's noglobals patch to support async tests as well
  * Landing Ariel's change - checks for global variable leakage.
  * qunit: run module-teardown in its own synchronize block to synchronize with async tests (ugh)
  * qunit: same: equiv - completely refactored in the testrunner.
  * testrunner.js:     - Update equiv to support Date and RegExp.     - Change behavior when comparing function:         - abort when in an instance of Object (when references comparison failed)         - skip otherwise (like before)
  * qunit: code refactoring and cleanup
  * QUnit: update equiv to latest version, handling multiple arguments and NaN, see http://philrathe.com/articles/equiv
  * QUnit: cleanup, deprecating compare, compare2 and serialArray: usage now throws an error with a helpful message
  * QUnit: optional timeout argument for stop, while making tests undetermined, useful for debugging
  * QUnit: added toolbar with "hide passed tests" checkbox to help focus on failed tests
  * QUnit: minor output formatting
  * QUnit: adding same-assertion for a recursive comparison of primitive values, arrays  and objects, thanks to Philippe Rathé for the contribution, including tests
  * QUnit: adding same-assertion for a recursive comparison of primitive values, arrays  and objects, thanks to Philippe Rathé for the contribution, including tests
  * QUnit: adding same-assertion for a recursive comparison of primitive values, arrays  and objects, thanks to Philippe Rathé for the contribution, including tests
  * qunit: use window.load to initialize tests, allowing other code to run on document-ready before starting to run tests
  * qunit: allow either setup or teardown, instead of both or nothing
  * qunit: make everything private by default, expose only public API; removed old timeout-option (non-deterministic, disabled for a long time anyway); use local $ reference instead of global jQuery reference; minor code cleanup (var config instead of _config; queue.shift instead of slice)
  * qunit: added support for module level setup/teardown callbacks
  * qunit: modified example for equals to avoid confusion with parameter ordering
  * qunit: added id/classes to result element to enable integration with browser automation tools, see http://docs.jquery.com/QUnit#Integration_into_Browser_Automation_Tools
  * qunit: replaced $ alias with jQuery (merged from jquery/test/data/testrunner.js)
  * qunit: fixed inline documentation for equals
  * qunit testrunner - catch and log possible error during reset()
  * QUnit: Switched out Date and Rev for Id.
  * qunit: when errors are thrown in a test, the message is successfully show on all browsers.
  * qunit: added license header
  * qunit: moved jquery testrunner to top-level project, see http://docs.jquery.com/QUnit
  * Share project 'qunit' into 'https://jqueryjs.googlecode.com/svn'
