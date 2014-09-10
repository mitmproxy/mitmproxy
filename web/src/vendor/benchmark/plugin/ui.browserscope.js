(function(window, document) {

  /** Cache used by various methods */
  var cache = {
    'counter': 0,
    'lastAction': 'load',
    'lastChart': 'bar',
    'lastFilterBy': 'all',
    'responses': { /* 'all': null, 'desktop': null, 'major': null, ... */ },
    'timers': { /* 'cleanup': null, 'load': null, 'post': null, ... */ },
    'trash': createElement('div')
  };

  /**
   * Used to filter Browserscope results by browser category.
   *
   * @see http://www.browserscope.org/user/tests/howto#urlparams
   */
  var filterMap = {
    'all': 3,
    'desktop': 'top-d',
    'family': 0,
    'major': 1,
    'minor': 2,
    'mobile': 'top-m',
    'popular': 'top',
    'prerelease': 'top-d-e'
  };

  /** Used to resolve a value's internal [[Class]] */
  var toString = {}.toString;

  /**
   * The `uaToken` is prepended to the value of the data cell of the Google
   * visualization data table object that matches the user's browser name. After
   * the chart is rendered the element containing the `uaToken` is assigned the
   * `ui.browserscope.uaClass` class name to allow for the creation of a visual
   * indicator to help the user more easily find their browser's results.
   */
  var uaToken = '\u2028';

  /** Math shortcuts */
  var floor = Math.floor,
      max = Math.max,
      min = Math.min;

  /** Utility shortcuts */
  var each = Benchmark.each,
      extend = Benchmark.extend,
      filter = Benchmark.filter,
      forOwn = Benchmark.forOwn,
      formatNumber = Benchmark.formatNumber,
      hasKey = Benchmark.hasKey,
      indexOf = Benchmark.indexOf,
      interpolate = Benchmark.interpolate,
      invoke = Benchmark.invoke,
      map = Benchmark.map,
      reduce = Benchmark.reduce;

  /*--------------------------------------------------------------------------*/

  /**
   * Registers an event listener.
   *
   * @private
   * @param {Element} element The element.
   * @param {String} eventName The name of the event to listen to.
   * @param {Function} handler The event handler.
   * @returns {Element} The element.
   */
  function addListener(element, eventName, handler) {
    if ((element = typeof element == 'string' ? query(element)[0] : element)) {
      if (typeof element.addEventListener != 'undefined') {
        element.addEventListener(eventName, handler, false);
      } else if (typeof element.attachEvent != 'undefined') {
        element.attachEvent('on' + eventName, handler);
      }
    }
    return element;
  }

  /**
   * Shortcut for `document.createElement()`.
   *
   * @private
   * @param {String} tagName The tag name of the element to create.
   * @param {String} name A name to assign to the element.
   * @param {Document|Element} context The document object used to create the element.
   * @returns {Element} Returns a new element.
   */
  function createElement(tagName, name, context) {
    var result;
    name && name.nodeType && (context = name, name = 0);
    context =  context ? context.ownerDocument || context : document;
    name || (name = '');

    try {
      // set name attribute for IE6/7
      result = context.createElement('<' + tagName + ' name="' + name + '">');
    } catch(e) {
      (result = context.createElement(tagName)).name = name;
    }
    return result;
  }

  /**
   * Creates a new style element.
   *
   * @private
   * @param {String} cssText The css text of the style element.
   * @param {Document|Element} context The document object used to create the element.
   * @returns {Element} Returns the new style element.
   */
  function createStyleSheet(cssText, context) {
    // use a text node, "x", to work around innerHTML issues with style elements
    // http://msdn.microsoft.com/en-us/library/ms533897(v=vs.85).aspx#1
    var div = createElement('div', context);
    div.innerHTML = 'x<style>' + cssText + '</style>';
    return div.lastChild;
  }

  /**
   * Gets the text content of an element.
   *
   * @private
   * @param {Element} element The element.
   * @returns {String} The text content of the element.
   */
  function getText(element) {
    element = query(element)[0];
    return element && (element.textContent || element.innerText) || '';
  }

  /**
   * Injects a script into the document.
   *
   * @private
   * @param {String} src The external script source.
   * @param {Object} sibling The element to inject the script after.
   * @param {Document} context The document object used to create the script element.
   * @returns {Object} The new script element.
   */
  function loadScript(src, sibling, context) {
    context = sibling ? sibling.ownerDocument || [sibling, sibling = 0][0] : context;
    var script = createElement('script', context),
        nextSibling = sibling ? sibling.nextSibling : query('script', context).pop();

    script.src = src;
    return (sibling || nextSibling).parentNode.insertBefore(script,  nextSibling);
  }

  /**
   * Queries the document for elements by id or tagName.
   *
   * @private
   * @param {String} selector The css selector to match.
   * @param {Document|Element} context The element whose descendants are queried.
   * @returns {Array} The array of results.
   */
  function query(selector, context) {
    var result = [];
    selector || (selector = '');
    context = typeof context == 'string' ? query(context)[0] : context || document;

    if (selector.nodeType) {
      result = [selector];
    }
    else if (context) {
      each(selector.split(','), function(selector) {
        each(/^#/.test(selector)
            ? [context.getElementById(selector.slice(1))]
            : context.getElementsByTagName(selector), function(node) {
          result.push(node);
        });
      });
    }
    return result;
  }

  /**
   * Set an element's innerHTML property.
   *
   * @private
   * @param {Element} element The element.
   * @param {String} html The HTML to set.
   * @param {Object} object The template object used to modify the html.
   * @returns {Element} The element.
   */
  function setHTML(element, html, object) {
    if ((element = query(element)[0])) {
      element.innerHTML = interpolate(html, object);
    }
    return element;
  }

  /**
   * Displays a message in the "results" element.
   *
   * @private
   * @param {String} text The text to display.
   * @param {Object} object The template object used to modify the text.
   */
  function setMessage(text, object) {
    var me = ui.browserscope,
        cont = me.container;

    if (cont) {
      cont.className = 'bs-rt-message';
      setHTML(cont, text, object);
    }
  }

  /*--------------------------------------------------------------------------*/

  /**
   * Adds a style sheet to the current chart and assigns the `ui.browserscope.uaClass`
   * class name to the chart element containing the user's browser name.
   *
   * @private
   * @returns {Boolean} Returns `true` if the operation succeeded, else `false`.
   */
  function addChartStyle() {
    var me = ui.browserscope,
        cssText = [],
        context = frames[query('iframe', me.container)[0].name].document,
        chartNodes = query('text,textpath', context),
        uaClass = me.uaClass,
        result = false;

    if (chartNodes.length) {
      // extract CSS rules for `uaClass`
      each(query('link,style'), function(node) {
        // avoid access denied errors on external style sheets
        // outside the same origin policy
        try {
          var sheet = node.sheet || node.styleSheet;
          each(sheet.cssRules || sheet.rules, function(rule) {
            if ((rule.selectorText || rule.cssText).indexOf('.' + uaClass) > -1) {
              cssText.push(rule.style && rule.style.cssText || /[^{}]*(?=})/.exec(rule.cssText) || '');
            }
          });
        } catch(e) { }
      });

      // insert custom style sheet
      query('head', context)[0].appendChild(
        createStyleSheet('.' + uaClass + '{' + cssText.join(';') + '}', context));

      // scan chart elements for a match
      each(chartNodes, function(node) {
        var nextSibling;
        if ((node.string || getText(node)).charAt(0) == uaToken) {
          // for VML
          if (node.string) {
            // IE requires reinserting the element to render correctly
            node.className = uaClass;
            nextSibling = node.nextSibling;
            node.parentNode.insertBefore(node.removeNode(), nextSibling);
          }
          // for SVG
          else {
            node.setAttribute('class', uaClass);
          }
          result = true;
        }
      });
    }
    return result;
  }

  /**
   * Periodically executed callback that removes injected script and iframe elements.
   *
   * @private
   */
  function cleanup() {
    var me = ui.browserscope,
        timings = me.timings,
        timers = cache.timers,
        trash = cache.trash,
        delay = timings.cleanup * 1e3;

    // remove injected scripts and old iframes when benchmarks aren't running
    if (timers.cleanup && !ui.running) {
      // if expired, destroy the element to prevent pseudo memory leaks.
      // http://dl.dropbox.com/u/513327/removechild_ie_leak.html
      each(query('iframe,script'), function(element) {
        var expire = +(/^browserscope-\d+-(\d+)$/.exec(element.name) || 0)[1] + max(delay, timings.timeout * 1e3);
        if (new Date > expire || /browserscope\.org|google\.com/.test(element.src)) {
          trash.appendChild(element);
          trash.innerHTML = '';
        }
      });
    }
    // schedule another round
    timers.cleanup = setTimeout(cleanup, delay);
  }

  /**
   * A simple data object cloning utility.
   *
   * @private
   * @param {Mixed} data The data object to clone.
   * @returns {Mixed} The cloned data object.
   */
  function cloneData(data) {
    var fn,
        ctor,
        result = data;

    if (isArray(data)) {
      result = map(data, cloneData);
    }
    else if (data === Object(data)) {
      ctor = data.constructor;
      result = ctor == Object ? {} : (fn = function(){}, fn.prototype = ctor.prototype, new fn);
      forOwn(data, function(value, key) {
        result[key] = cloneData(value);
      });
    }
    return result;
  }

  /**
   * Creates a Browserscope results object.
   *
   * @private
   * @returns {Object|Null} Browserscope results object or null.
   */
  function createSnapshot() {
    // clone benches, exclude those that are errored, unrun, or have hz of Infinity
    var benches = invoke(filter(ui.benchmarks, 'successful'), 'clone'),
        fastest = filter(benches, 'fastest'),
        slowest = filter(benches, 'slowest'),
        neither = filter(benches, function(bench) {
          return indexOf(fastest, bench) + indexOf(slowest, bench) == -2;
        });

    function merge(destination, source) {
      destination.count = source.count;
      destination.cycles = source.cycles;
      destination.hz = source.hz;
      destination.stats = extend({}, source.stats);
    }

    // normalize results on slowest in each category
    each(fastest.concat(slowest), function(bench) {
      merge(bench, indexOf(fastest, bench) > -1 ? fastest[fastest.length - 1] : slowest[0]);
    });

    // sort slowest to fastest
    // (a larger `mean` indicates a slower benchmark)
    neither.sort(function(a, b) {
      a = a.stats; b = b.stats;
      return (a.mean + a.moe > b.mean + b.moe) ? -1 : 1;
    });

    // normalize the leftover benchmarks
    reduce(neither, function(prev, bench) {
      // if the previous slower benchmark is indistinguishable from
      // the current then use the previous benchmark's values
      if (prev.compare(bench) == 0) {
        merge(bench, prev);
      }
      return bench;
    });

    // append benchmark ids for duplicate names or names with no alphanumeric/space characters
    // and use the upper limit of the confidence interval to compute a lower hz
    // to avoid recording inflated results caused by a high margin or error
    return reduce(benches, function(result, bench, key) {
      var stats = bench.stats;
      result || (result = {});
      key = toLabel(bench.name);
      result[key && !hasKey(result, key) ? key : key + bench.id ] = floor(1 / (stats.mean + stats.moe));
      return result;
    }, null);
  }

  /**
   * Retrieves the "cells" array from a given Google visualization data row object.
   *
   * @private
   * @param {Object} object The data row object.
   * @returns {Array} An array of cell objects.
   */
  function getDataCells(object) {
    // resolve cells by duck typing because of munged property names
    var result = [];
    forOwn(object, function(value) {
      return !(isArray(value) && (result = value));
    });
    // remove empty entries which occur when not all the tests are recorded
    return filter(result, Boolean);
  }

  /**
   * Retrieves the "labels" array from a given Google visualization data table object.
   *
   * @private
   * @param {Object} object The data table object.
   * @returns {Array} An array of label objects.
   */
  function getDataLabels(object) {
    var result = [],
        labelMap = {};

    // resolve labels by duck typing because of munged property names
    forOwn(object, function(value) {
      return !(isArray(value) && 0 in value && 'type' in value[0] && (result = value));
    });
    // create a data map of labels to names
    each(ui.benchmarks, function(bench) {
      var key = toLabel(bench.name);
      labelMap[key && !hasKey(labelMap, key) ? key : key + bench.id ] = bench.name;
    });
    // replace Browserscope's basic labels with benchmark names
    return each(result, function(cell) {
      var name = labelMap[cell.label];
      name && (cell.label = name);
    });
  }

  /**
   * Retrieves the "rows" array from a given Google visualization data table object.
   *
   * @private
   * @param {Object} object The data table object.
   * @returns {Array} An array of row objects.
   */
  function getDataRows(object) {
    var name,
        filterBy = cache.lastFilterBy,
        browserName = toBrowserName(getText(query('strong', '#bs-ua')[0]), filterBy),
        uaClass = ui.browserscope.uaClass,
        result = [];

    // resolve rows by duck typing because of munged property names
    forOwn(object, function(value, key) {
      return !(isArray(value) && 0 in value && !('type' in value[0]) && (name = key, result = value));
    });
    // remove empty rows and set the `p.className` on the browser
    // name cell that matches the user's browser name
    if (result.length) {
      result = object[name] = filter(result, function(value) {
        var cells = getDataCells(value),
            first = cells[0],
            second = cells[1];

        // cells[0] is the browser name cell so instead we check cells[1]
        // for the presence of ops/sec data to determine if a row is empty or not
        if (first && second && second.f) {
          delete first.p.className;
          if (browserName == toBrowserName(first.f, filterBy)) {
            first.p.className = uaClass;
          }
          return true;
        }
      });
    }
    return result;
  }

  /**
   * Checks if a value has an internal [[Class]] of Array.
   *
   * @private
   * @param {Mixed} value The value to check.
   * @returns {Boolean} Returns `true` if the value has an internal [[Class]] of
   *  Array, else `false`.
   */
  function isArray(value) {
    return toString.call(value) == '[object Array]';
  }

  /**
   * Executes a callback at a given delay interval until it returns `false`.
   *
   * @private
   * @param {Function} callback The function called every poll interval.
   * @param {Number} delay The delay between callback calls (secs).
   */
  function poll(callback, delay) {
    function poller(init) {
      if (init || callback() !== false) {
        setTimeout(poller, delay * 1e3);
      }
    }
    poller(true);
  }

  /**
   * Cleans up the last action and sets the current action.
   *
   * @private
   * @param {String} action The current action.
   */
  function setAction(action) {
    clearTimeout(cache.timers[cache.lastAction]);
    cache.lastAction = action;
  }

  /**
   * Converts the browser name version number to the format allowed by the
   * specified filter.
   *
   * @private
   * @param {String} name The full browser name .
   * @param {String} filterBy The filter formating rules to apply.
   * @returns {String} The converted browser name.
   */
  function toBrowserName(name, filterBy) {
    name || (name = '');
    if (filterBy == 'all') {
      // truncate something like 1.0.0 to 1
      name = name.replace(/(\d+)[.0]+$/, '$1');
    }
    else if (filterBy == 'family') {
      // truncate something like XYZ 1.2 to XYZ
      name = name.replace(/[.\d\s]+$/, '');
    }
    else if (/minor|popular/.test(filterBy) && /\d+(?:\.[1-9])+$/.test(name)) {
      // truncate something like 1.2.3 to 1.2
      name = name.replace(/(\d+\.[1-9])(\.[.\d]+$)/, '$1');
    }
    else {
      // truncate something like 1.0 to 1 or 1.2.3 to 1 but leave something like 1.2 alone
      name = name.replace(/(\d+)(?:(\.[1-9]$)|(\.[.\d]+$))/, '$1$2');
    }
    return name;
  }

  /**
   * Replaces non-alphanumeric characters with spaces because Browserscope labels
   * can only contain alphanumeric characters and spaces.
   *
   * @private
   * @param {String} text The text to be converted.
   * @returns {String} The Browserscope safe label text.
   * @see http://code.google.com/p/browserscope/issues/detail?id=271
   */
  function toLabel(text) {
    return (text || '').replace(/[^a-z0-9]+/gi, ' ');
  }

  /*--------------------------------------------------------------------------*/

  /**
   * Loads Browserscope's cumulative results table.
   *
   * @static
   * @memberOf ui.browserscope
   * @param {Object} options The options object.
   */
  function load(options) {
    options || (options = {});

    var fired,
        me = ui.browserscope,
        cont = me.container,
        filterBy = cache.lastFilterBy = options.filterBy || cache.lastFilterBy,
        responses = cache.responses,
        response = cache.responses[filterBy],
        visualization = window.google && google.visualization;

    function onComplete(response) {
      var lastResponse = responses[filterBy];
      if (!fired) {
        // set the fired flag to avoid Google's own timeout
        fired = true;
        // render if the filter is still the same, else cache the result
        if (filterBy == cache.lastFilterBy) {
          me.render({ 'force': true, 'response': lastResponse || response });
        } else if(!lastResponse && response && !response.isError()) {
          responses[filterBy] = response;
        }
      }
    }

    // set last action in case the load fails and a retry is needed
    setAction('load');

    // exit early if there is no container element or the response is cached
    // and retry if the visualization library hasn't loaded yet
    if (!cont || !visualization || !visualization.Query || response) {
      cont && onComplete(response);
    }
    else if (!ui.running) {
      // set our own load timeout to display an error message and retry loading
      cache.timers.load = setTimeout(onComplete, me.timings.timeout * 1e3);
      // set "loading" message and attempt to load Browserscope data
      setMessage(me.texts.loading);
      // request Browserscope pass chart data to `google.visualization.Query.setResponse()`
      (new visualization.Query(
        '//www.browserscope.org/gviz_table_data?category=usertest_' + me.key + '&v=' + filterMap[filterBy],
        { 'sendMethod': 'scriptInjection' }
      ))
      .send(onComplete);
    }
  }

  /**
   * Creates a Browserscope beacon and posts the benchmark results.
   *
   * @static
   * @memberOf ui.browserscope
   */
  function post() {
    var idoc,
        iframe,
        body = document.body,
        me = ui.browserscope,
        key = me.key,
        timings = me.timings,
        name = 'browserscope-' + (cache.counter++) + '-' + (+new Date),
        snapshot = createSnapshot();

    // set last action in case the post fails and a retry is needed
    setAction('post');

    if (key && snapshot && me.postable && !ui.running && !/Simulator/i.test(Benchmark.platform)) {
      // create new beacon
      // (the name contains a timestamp so `cleanup()` can determine when to remove it)
      iframe = createElement('iframe', name);
      body.insertBefore(iframe, body.firstChild);
      idoc = frames[name].document;
      iframe.style.display = 'none';

      // expose results snapshot
      me.snapshot = snapshot;
      // set "posting" message and attempt to post the results snapshot
      setMessage(me.texts.post);
      // Note: We originally created an iframe to avoid Browerscope's old limit
      // of one beacon per page load. It's currently used to implement custom
      // request timeout and retry routines.
      idoc.write(interpolate(
        // the doctype is required so Browserscope detects the correct IE compat mode
        '#{doctype}<title></title><body><script>' +
        'with(parent.ui.browserscope){' +
        'var _bTestResults=snapshot,' +
        '_bC=function(){clearTimeout(_bT);parent.setTimeout(function(){purge();load()},#{refresh}*1e3)},' +
        '_bT=setTimeout(function(){_bC=function(){};render()},#{timeout}*1e3)' +
        '}<\/script>' +
        '<script src=//www.browserscope.org/user/beacon/#{key}?callback=_bC><\/script>',
        {
          'doctype': /css/i.test(document.compatMode) ? '<!doctype html>' : '',
          'key': key,
          'refresh': timings.refresh,
          'timeout': timings.timeout
        }
      ));
      // avoid the IE spinner of doom
      // http://www.google.com/search?q=IE+throbber+of+doom
      idoc.close();
    }
    else {
      me.load();
    }
  }

  /**
   * Purges the Browserscope response cache.
   *
   * @static
   * @memberOf ui.browserscope
   * @param {String} key The key of a single cache entry to clear.
   */
  function purge(key) {
    // we don't pave the cache object with a new one to preserve existing references
    var responses = cache.responses;
    if (key) {
      delete responses[key];
    } else {
      forOwn(responses, function(value, key) {
        delete responses[key];
      });
    }
  }

  /**
   * Renders the cumulative results table.
   * (tweak the dimensions and styles to best fit your environment)
   *
   * @static
   * @memberOf ui.browserscope
   * @param {Object} options The options object.
   */
  function render(options) {
    options || (options = {});

    // coordinates, dimensions, and sizes are in px
    var areaHeight,
        cellWidth,
        data,
        labels,
        rowCount,
        rows,
        me = ui.browserscope,
        cont = me.container,
        responses = cache.responses,
        visualization = window.google && google.visualization,
        lastChart = cache.lastChart,
        chart = cache.lastChart = options.chart || lastChart,
        lastFilterBy = cache.lastFilterBy,
        filterBy = cache.lastFilterBy = options.filterBy || lastFilterBy,
        lastResponse = responses[filterBy],
        response = responses[filterBy] = 'response' in options ? (response = options.response) && !response.isError() && response : lastResponse,
        areaWidth = '100%',
        cellHeight = 80,
        fontSize = 13,
        height = 'auto',
        hTitle = 'operations per second (higher is better)',
        hTitleHeight = 48,
        left = 240,
        legend = 'top',
        maxChars = 0,
        maxCharsLimit = 20,
        maxOps = 0,
        minHeight = 480,
        minWidth = cont && cont.offsetWidth || 948,
        title = '',
        top = 50,
        vTitle = '',
        vTitleWidth = 48,
        width = minWidth;

    function retry(force) {
      var action = cache.lastAction;
      if (force || ui.running) {
        cache.timers[action] = setTimeout(retry, me.timings.retry * 1e3);
      } else {
        me[action].apply(me, action == 'render' ? [options] : []);
      }
    }

    // set action to clear any timeouts and prep for retries
    setAction(response ? 'render' : cache.lastAction);

    // exit early if there is no container element, the data filter has changed or nothing has changed
    if (!cont || visualization && (filterBy != lastFilterBy ||
        (!options.force && chart == lastChart && response == lastResponse))) {
      cont && filterBy != lastFilterBy && load(options);
    }
    // retry if response data is empty/errored or the visualization library hasn't loaded yet
    else if (!response || !visualization) {
      // set error message for empty/errored response
      !response && visualization && setMessage(me.texts.error);
      retry(true);
    }
    // visualization chart gallary
    // http://code.google.com/apis/chart/interactive/docs/gallery.html
    else if (!ui.running) {
      cont.className = '';
      data = cloneData(response.getDataTable());
      labels = getDataLabels(data);
      rows = getDataRows(data);
      rowCount = rows.length;
      chart = chart.charAt(0).toUpperCase() + chart.slice(1).toLowerCase();

      // adjust data for non-tabular displays
      if (chart != 'Table') {
        // remove "# Tests" run count label (without label data the row will be ignored)
        labels.pop();

        // modify row data
        each(rows, function(row) {
          each(getDataCells(row), function(cell, index, cells) {
            var lastIndex = cells.length - 1;

            // cells[1] through cells[lastIndex - 1] are ops/sec cells
            if (/^[\d.,]+$/.test(cell.f)) {
              // assign ops/sec as cell value
              cell.v = +cell.f.replace(/,/g, '');
              // add rate to the text
              cell.f += ' ops/sec';
              // capture highest ops value to use when computing the left coordinate
              maxOps = max(maxOps, cell.v);
            }
            // cells[0] is the browser name cell
            // cells[lastIndex] is the run count cell and has no `f` property
            else if (cell.f) {
              // add test run count to browser name
              cell.f += chart == 'Pie' ? '' : ' (' + (cells[lastIndex].v || 1) + ')';
              // capture longest char count to use when computing left coordinate/cell width
              maxChars = min(maxCharsLimit, max(maxChars, cell.f.length));
            }
            // compute sum of all ops/sec for pie charts
            if (chart == 'Pie') {
              if (index == lastIndex) {
                cells[1].f = formatNumber(cells[1].v) + ' total ops/sec';
              } else if (index > 1 && typeof cell.v == 'number') {
                cells[1].v += cell.v;
              }
            }
            // if the browser name matches the user's browser then style it
            if (cell.p && cell.p.className) {
              // prefix the browser name with a line separator (\u2028) because it's not rendered
              // (IE may render a negligible space in the tooltip of browser names truncated with ellipsis)
              cell.f = uaToken + cell.f;
              // poll until the chart elements exist and are styled
              poll(function() { return !addChartStyle(); }, 0.01);
            }
          });
        });

        // adjust captions and chart dimensions
        if (chart == 'Bar') {
          // use minHeight to avoid sizing issues when there is only 1 bar
          height = max(minHeight, top + (rowCount * cellHeight));
          // compute left by adding the longest approximate vAxis text width and
          // a right pad of 10px
          left = (maxChars * (fontSize / 1.6)) + 10;
          // get percentage of width left after subtracting the chart's left
          // coordinate and room for the ops/sec number
          areaWidth = (100 - (((left + 50) / width) * 100)) + '%';
        }
        else {
          // swap captions (the browser list caption is blank to conserve space)
          vTitle = [hTitle, hTitle = vTitle][0];
          height = minHeight;

          if (chart == 'Pie') {
            legend = 'right';
            title = 'Total operations per second by browser (higher is better)';
          }
          else {
            hTitleHeight = 28;
            // compute left by getting the sum of the horizontal space wanted
            // for the vAxis title's width, the approximate vAxis text width, and
            // the 13px gap between the chart and the right side of the vAxis text
            left = vTitleWidth + (formatNumber(maxOps).length * (fontSize / 1.6)) + 13;
            // compute cell width by adding the longest approximate hAxis text
            // width and wiggle room of 26px
            cellWidth = (maxChars * (fontSize / 2)) + 26;
            // use minWidth to avoid clipping the key
            width = max(minWidth, left + (rowCount * cellWidth));
          }
        }
        // get percentage of height left after subtracting the vertical space wanted
        // for the hAxis title's height, text size, the chart's top coordinate,
        // and the 8px gap between the chart and the top of the hAxis text
        areaHeight = (100 - (((hTitleHeight + fontSize + top + 8) / height) * 100)) + '%';
        // make chart type recognizable
        chart += 'Chart';
      }

      if (rowCount && visualization[chart]) {
         new visualization[chart](cont).draw(data, {
          'colors': ui.browserscope.colors,
          'fontSize': fontSize,
          'is3D': true,
          'legend': legend,
          'height': height,
          'title': title,
          'width': width,
          'chartArea': { 'height': areaHeight, 'left': left, 'top': top, 'width': areaWidth },
          'hAxis': { 'baseline': 0, 'title': hTitle },
          'vAxis': { 'baseline': 0, 'title': vTitle }
        });
      } else {
        setMessage(me.texts.empty);
      }
    }
  }

  /*--------------------------------------------------------------------------*/

  // expose
  ui.browserscope = {

    /**
     * Your Browserscope API key.
     *
     * @memberOf ui.browserscope
     * @type String
     */
    'key': '',

    /**
     * A flag to indicate if posting is enabled or disabled.
     *
     * @memberOf ui.browserscope
     * @type Boolean
     */
    'postable': true,

    /**
     * The selector of the element to contain the entire Browserscope UI.
     *
     * @memberOf ui.browserscope
     * @type String
     */
    'selector': '',

    /**
     * The class name used to style the user's browser name when it appears
     * in charts.
     *
     * @memberOf ui.browserscope
     * @type String
     */
    'uaClass': 'rt-ua-cur',

    /**
     * Object containing various timings settings.
     *
     * @memberOf ui.browserscope
     * @type Object
     */
    'timings': {

      /**
       * The delay between removing abandoned script and iframe elements (secs).
       *
       * @memberOf ui.browserscope.timings
       * @type Number
       */
      'cleanup': 10,

      /**
       * The delay before refreshing the cumulative results after posting (secs).
       *
       * @memberOf ui.browserscope.timings
       * @type Number
       */
      'refresh': 3,

      /**
       * The delay between load attempts (secs).
       *
       * @memberOf ui.browserscope.timings
       * @type Number
       */
      'retry': 5,

      /**
       * The time to wait for a request to finish (secs).
       *
       * @memberOf ui.browserscope.timings
       * @type Number
       */
      'timeout': 10
    },

    /**
     * Object containing various text messages.
     *
     * @memberOf ui.browserscope
     * @type Object
     */
    'texts': {

      /**
       * The text shown when their is no recorded data available to report.
       *
       * @memberOf ui.browserscope.texts
       * @type String
       */
      'empty': 'No data available',

      /**
       * The text shown when the cumulative results data cannot be retrieved.
       *
       * @memberOf ui.browserscope.texts
       * @type String
       */
      'error': 'The get/post request has failed :(',

      /**
       * The text shown while waiting for the cumulative results data to load.
       *
       * @memberOf ui.browserscope.texts
       * @type String
       */
      'loading': 'Loading cumulative results data&hellip;',

      /**
       * The text shown while posting the results snapshot to Browserscope.
       *
       * @memberOf ui.browserscope.texts
       * @type String
       */
      'post': 'Posting results snapshot&hellip;',

      /**
       * The text shown while benchmarks are running.
       *
       * @memberOf ui.browserscope.texts
       * @type String
       */
      'wait': 'Benchmarks running. Please wait&hellip;'
    },

    // loads cumulative results table
    'load': load,

    // posts benchmark snapshot to Browserscope
    'post': post,

    // purges the Browserscope response cache
    'purge': purge,

    // renders cumulative results table
    'render': render
  };

  /*--------------------------------------------------------------------------*/

  addListener(window, 'load', function() {
    var me = ui.browserscope,
        key = me.key,
        placeholder = key && query(me.selector)[0];

    // create results html
    if (placeholder) {
      setHTML(placeholder,
        '<h1 id=bs-logo><a href=//www.browserscope.org/user/tests/table/#{key}>' +
        '<span>Browserscope</span></a></h1>' +
        '<div class=bs-rt><div id=bs-chart></div></div>',
        { 'key': key });

      // the element the charts are inserted into
      me.container = query('#bs-chart')[0];

      // Browserscope's UA div is inserted before an element with the id of "bs-ua-script"
      loadScript('//www.browserscope.org/ua?o=js', me.container).id = 'bs-ua-script';

      // the "autoload" string can be created with
      // http://code.google.com/apis/loader/autoloader-wizard.html
      loadScript('//www.google.com/jsapi?autoload=' + encodeURIComponent('{' +
        'modules:[{' +
          'name:"visualization",' +
          'version:1,' +
          'packages:["corechart","table"],' +
          'callback:ui.browserscope.load' +
        '}]' +
      '}'));

      // init garbage collector
      cleanup();
    }
  });

  // hide the chart while benchmarks are running
  ui.on('start', function() {
    setMessage(ui.browserscope.texts.wait);
  })
  .on('abort', function() {
    ui.browserscope.render({ 'force': true });
  });

}(this, document));
