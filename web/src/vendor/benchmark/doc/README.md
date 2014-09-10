# Benchmark.js <sup>v1.0.0</sup>

<!-- div -->


<!-- div -->

## <a id="Benchmark"></a>`Benchmark`
* [`Benchmark`](#benchmarkname-fn--options)
* [`Benchmark.version`](#benchmarkversion)
* [`Benchmark.deepClone`](#benchmarkdeepclonevalue)
* [`Benchmark.each`](#benchmarkeachobject-callback-thisarg)
* [`Benchmark.extend`](#benchmarkextenddestination--source)
* [`Benchmark.filter`](#benchmarkfilterarray-callback-thisarg)
* [`Benchmark.forEach`](#benchmarkforeacharray-callback-thisarg)
* [`Benchmark.formatNumber`](#benchmarkformatnumbernumber)
* [`Benchmark.forOwn`](#benchmarkforownobject-callback-thisarg)
* [`Benchmark.hasKey`](#benchmarkhaskeyobject-key)
* [`Benchmark.indexOf`](#benchmarkindexofarray-value--fromindex0)
* [`Benchmark.interpolate`](#benchmarkinterpolatestring-object)
* [`Benchmark.invoke`](#benchmarkinvokebenches-name--arg1-arg2-)
* [`Benchmark.join`](#benchmarkjoinobject--separator1--separator2:)
* [`Benchmark.map`](#benchmarkmaparray-callback-thisarg)
* [`Benchmark.pluck`](#benchmarkpluckarray-property)
* [`Benchmark.reduce`](#benchmarkreducearray-callback-accumulator)

<!-- /div -->


<!-- div -->

## `Benchmark.prototype`
* [`Benchmark.prototype.aborted`](#benchmarkprototypeaborted)
* [`Benchmark.prototype.compiled`](#benchmarkprototypecompiled)
* [`Benchmark.prototype.count`](#benchmarkprototypecount)
* [`Benchmark.prototype.cycles`](#benchmarkprototypecycles)
* [`Benchmark.prototype.fn`](#benchmarkprototypefn)
* [`Benchmark.prototype.hz`](#benchmarkprototypehz)
* [`Benchmark.prototype.running`](#benchmarkprototyperunning)
* [`Benchmark.prototype.setup`](#benchmarkprototypesetup)
* [`Benchmark.prototype.teardown`](#benchmarkprototypeteardown)
* [`Benchmark.prototype.abort`](#benchmarkprototypeabort)
* [`Benchmark.prototype.clone`](#benchmarkprototypecloneoptions)
* [`Benchmark.prototype.compare`](#benchmarkprototypecompareother)
* [`Benchmark.prototype.emit`](#benchmarkprototypeemittype)
* [`Benchmark.prototype.listeners`](#benchmarkprototypelistenerstype)
* [`Benchmark.prototype.off`](#benchmarkprototypeofftype-listener)
* [`Benchmark.prototype.on`](#benchmarkprototypeontype-listener)
* [`Benchmark.prototype.reset`](#benchmarkprototypereset)
* [`Benchmark.prototype.run`](#benchmarkprototyperunoptions)
* [`Benchmark.prototype.toString`](#benchmarkprototypetostring)

<!-- /div -->


<!-- div -->

## `Benchmark.options`
* [`Benchmark.options`](#benchmarkoptions)
* [`Benchmark.options.async`](#benchmarkoptionsasync)
* [`Benchmark.options.defer`](#benchmarkoptionsdefer)
* [`Benchmark.options.delay`](#benchmarkoptionsdelay)
* [`Benchmark.options.id`](#benchmarkoptionsid)
* [`Benchmark.options.initCount`](#benchmarkoptionsinitcount)
* [`Benchmark.options.maxTime`](#benchmarkoptionsmaxtime)
* [`Benchmark.options.minSamples`](#benchmarkoptionsminsamples)
* [`Benchmark.options.minTime`](#benchmarkoptionsmintime)
* [`Benchmark.options.name`](#benchmarkoptionsname)
* [`Benchmark.options.onAbort`](#benchmarkoptionsonabort)
* [`Benchmark.options.onComplete`](#benchmarkoptionsoncomplete)
* [`Benchmark.options.onCycle`](#benchmarkoptionsoncycle)
* [`Benchmark.options.onError`](#benchmarkoptionsonerror)
* [`Benchmark.options.onReset`](#benchmarkoptionsonreset)
* [`Benchmark.options.onStart`](#benchmarkoptionsonstart)

<!-- /div -->


<!-- div -->

## `Benchmark.platform`
* [`Benchmark.platform`](#benchmarkplatform)
* [`Benchmark.platform.description`](#benchmarkplatformdescription)
* [`Benchmark.platform.layout`](#benchmarkplatformlayout)
* [`Benchmark.platform.manufacturer`](#benchmarkplatformmanufacturer)
* [`Benchmark.platform.name`](#benchmarkplatformname)
* [`Benchmark.platform.os`](#benchmarkplatformos)
* [`Benchmark.platform.prerelease`](#benchmarkplatformprerelease)
* [`Benchmark.platform.product`](#benchmarkplatformproduct)
* [`Benchmark.platform.version`](#benchmarkplatformversion)
* [`Benchmark.platform.toString`](#benchmarkplatformtostring)

<!-- /div -->


<!-- div -->

## `Benchmark.support`
* [`Benchmark.support`](#benchmarksupport)
* [`Benchmark.support.air`](#benchmarksupportair)
* [`Benchmark.support.argumentsClass`](#benchmarksupportargumentsclass)
* [`Benchmark.support.browser`](#benchmarksupportbrowser)
* [`Benchmark.support.charByIndex`](#benchmarksupportcharbyindex)
* [`Benchmark.support.charByOwnIndex`](#benchmarksupportcharbyownindex)
* [`Benchmark.support.decompilation`](#benchmarksupportdecompilation)
* [`Benchmark.support.descriptors`](#benchmarksupportdescriptors)
* [`Benchmark.support.getAllKeys`](#benchmarksupportgetallkeys)
* [`Benchmark.support.iteratesOwnLast`](#benchmarksupportiteratesownfirst)
* [`Benchmark.support.java`](#benchmarksupportjava)
* [`Benchmark.support.nodeClass`](#benchmarksupportnodeclass)
* [`Benchmark.support.timeout`](#benchmarksupporttimeout)

<!-- /div -->


<!-- div -->

## `Benchmark.prototype.error`
* [`Benchmark.prototype.error`](#benchmarkprototypeerror)

<!-- /div -->


<!-- div -->

## `Benchmark.prototype.stats`
* [`Benchmark.prototype.stats`](#benchmarkprototypestats)
* [`Benchmark.prototype.stats.deviation`](#benchmark-statsdeviation)
* [`Benchmark.prototype.stats.mean`](#benchmark-statsmean)
* [`Benchmark.prototype.stats.moe`](#benchmark-statsmoe)
* [`Benchmark.prototype.stats.rme`](#benchmark-statsrme)
* [`Benchmark.prototype.stats.sample`](#benchmark-statssample)
* [`Benchmark.prototype.stats.sem`](#benchmark-statssem)
* [`Benchmark.prototype.stats.variance`](#benchmark-statsvariance)

<!-- /div -->


<!-- div -->

## `Benchmark.prototype.times`
* [`Benchmark.prototype.times`](#benchmarkprototypetimes)
* [`Benchmark.prototype.times.cycle`](#benchmark-timescycle)
* [`Benchmark.prototype.times.elapsed`](#benchmark-timeselapsed)
* [`Benchmark.prototype.times.period`](#benchmark-timesperiod)
* [`Benchmark.prototype.times.timeStamp`](#benchmark-timestimestamp)

<!-- /div -->


<!-- div -->

## `Benchmark.Deferred`
* [`Benchmark.Deferred`](#benchmarkdeferredclone)

<!-- /div -->


<!-- div -->

## `Benchmark.Deferred.prototype`
* [`Benchmark.Deferred.prototype.benchmark`](#benchmarkdeferredprototypebenchmark)
* [`Benchmark.Deferred.prototype.cycles`](#benchmarkdeferredprototypecycles)
* [`Benchmark.Deferred.prototype.elapsed`](#benchmarkdeferredprototypeelapsed)
* [`Benchmark.Deferred.prototype.resolve`](#benchmarkdeferredprototyperesolve)
* [`Benchmark.Deferred.prototype.timeStamp`](#benchmarkdeferredprototypetimestamp)

<!-- /div -->


<!-- div -->

## `Benchmark.Event`
* [`Benchmark.Event`](#benchmarkeventtype)

<!-- /div -->


<!-- div -->

## `Benchmark.Event.prototype`
* [`Benchmark.Event.prototype.aborted`](#benchmarkeventprototypeaborted)
* [`Benchmark.Event.prototype.cancelled`](#benchmarkeventprototypecancelled)
* [`Benchmark.Event.prototype.result`](#benchmarkeventprototyperesult)
* [`Benchmark.Event.prototype.timeStamp`](#benchmarkeventprototypetimestamp)
* [`Benchmark.Event.prototype.type`](#benchmarkeventprototypetype)

<!-- /div -->


<!-- div -->

## `Benchmark.Event.prototype.currentTarget`
* [`Benchmark.Event.prototype.currentTarget`](#benchmarkeventprototypecurrenttarget)

<!-- /div -->


<!-- div -->

## `Benchmark.Event.prototype.target`
* [`Benchmark.Event.prototype.target`](#benchmarkeventprototypetarget)

<!-- /div -->


<!-- div -->

## `Benchmark.Suite`
* [`Benchmark.Suite`](#benchmarksuitename--options)

<!-- /div -->


<!-- div -->

## `Benchmark.Suite.prototype`
* [`Benchmark.Suite.prototype.aborted`](#benchmarksuiteprototypeaborted)
* [`Benchmark.Suite.prototype.length`](#benchmarksuiteprototypelength)
* [`Benchmark.Suite.prototype.running`](#benchmarksuiteprototyperunning)
* [`Benchmark.Suite.prototype.abort`](#benchmarksuiteprototypeabort)
* [`Benchmark.Suite.prototype.add`](#benchmarksuiteprototypeaddname-fn--options)
* [`Benchmark.Suite.prototype.clone`](#benchmarksuiteprototypecloneoptions)
* [`Benchmark.Suite.prototype.emit`](#benchmarkprototypeemittype)
* [`Benchmark.Suite.prototype.filter`](#benchmarksuiteprototypefiltercallback)
* [`Benchmark.Suite.prototype.forEach`](#benchmarksuiteprototypeforeachcallback)
* [`Benchmark.Suite.prototype.indexOf`](#benchmarksuiteprototypeindexofvalue)
* [`Benchmark.Suite.prototype.invoke`](#benchmarksuiteprototypeinvokename--arg1-arg2-)
* [`Benchmark.Suite.prototype.join`](#benchmarksuiteprototypejoinseparator-)
* [`Benchmark.Suite.prototype.listeners`](#benchmarkprototypelistenerstype)
* [`Benchmark.Suite.prototype.map`](#benchmarksuiteprototypemapcallback)
* [`Benchmark.Suite.prototype.off`](#benchmarkprototypeofftype-listener)
* [`Benchmark.Suite.prototype.on`](#benchmarkprototypeontype-listener)
* [`Benchmark.Suite.prototype.pluck`](#benchmarksuiteprototypepluckproperty)
* [`Benchmark.Suite.prototype.pop`](#benchmarksuiteprototypepop)
* [`Benchmark.Suite.prototype.push`](#benchmarksuiteprototypepush)
* [`Benchmark.Suite.prototype.reduce`](#benchmarksuiteprototypereducecallback-accumulator)
* [`Benchmark.Suite.prototype.reset`](#benchmarksuiteprototypereset)
* [`Benchmark.Suite.prototype.reverse`](#benchmarksuiteprototypereverse)
* [`Benchmark.Suite.prototype.run`](#benchmarksuiteprototyperunoptions)
* [`Benchmark.Suite.prototype.shift`](#benchmarksuiteprototypeshift)
* [`Benchmark.Suite.prototype.slice`](#benchmarksuiteprototypeslicestart-end)
* [`Benchmark.Suite.prototype.sort`](#benchmarksuiteprototypesortcomparefnnull)
* [`Benchmark.Suite.prototype.splice`](#benchmarksuiteprototypesplicestart-deletecount--val1-val2-)
* [`Benchmark.Suite.prototype.unshift`](#benchmarksuiteprototypeunshift)

<!-- /div -->


<!-- div -->

## `Benchmark.Suite.options`
* [`Benchmark.Suite.options`](#benchmarksuiteoptions)
* [`Benchmark.Suite.options.name`](#benchmarksuiteoptionsname)

<!-- /div -->


<!-- /div -->


<!-- div -->


<!-- div -->

## `Benchmark`

<!-- div -->

### <a id="benchmarkname-fn--options"></a>`Benchmark(name, fn [, options={}])`
<a href="#benchmarkname-fn--options">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L404 "View in source") [&#x24C9;][1]

The Benchmark constructor.

#### Arguments
1. `name` *(String)*: A name to identify the benchmark.
2. `fn` *(Function|String)*: The test to benchmark.
3. `[options={}]` *(Object)*: Options object.

#### Example
```js
// basic usage (the `new` operator is optional)
var bench = new Benchmark(fn);

// or using a name first
var bench = new Benchmark('foo', fn);

// or with options
var bench = new Benchmark('foo', fn, {

  // displayed by Benchmark#toString if `name` is not available
  'id': 'xyz',

  // called when the benchmark starts running
  'onStart': onStart,

  // called after each run cycle
  'onCycle': onCycle,

  // called when aborted
  'onAbort': onAbort,

  // called when a test errors
  'onError': onError,

  // called when reset
  'onReset': onReset,

  // called when the benchmark completes running
  'onComplete': onComplete,

  // compiled/called before the test loop
  'setup': setup,

  // compiled/called after the test loop
  'teardown': teardown
});

// or name and options
var bench = new Benchmark('foo', {

  // a flag to indicate the benchmark is deferred
  'defer': true,

  // benchmark test function
  'fn': function(deferred) {
    // call resolve() when the deferred test is finished
    deferred.resolve();
  }
});

// or options only
var bench = new Benchmark({

  // benchmark name
  'name': 'foo',

  // benchmark test as a string
  'fn': '[1,2,3,4].sort()'
});

// a test's `this` binding is set to the benchmark instance
var bench = new Benchmark('foo', function() {
  'My name is '.concat(this.name); // My name is foo
});
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkversion"></a>`Benchmark.version`
<a href="#benchmarkversion">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3268 "View in source") [&#x24C9;][1]

*(String)*: The semantic version number.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkdeepclonevalue"></a>`Benchmark.deepClone(value)`
<a href="#benchmarkdeepclonevalue">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1225 "View in source") [&#x24C9;][1]

A deep clone utility.

#### Arguments
1. `value` *(Mixed)*: The value to clone.

#### Returns
*(Mixed)*: The cloned value.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkeachobject-callback-thisarg"></a>`Benchmark.each(object, callback, thisArg)`
<a href="#benchmarkeachobject-callback-thisarg">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1400 "View in source") [&#x24C9;][1]

An iteration utility for arrays and objects. Callbacks may terminate the loop by explicitly returning `false`.

#### Arguments
1. `object` *(Array|Object)*: The object to iterate over.
2. `callback` *(Function)*: The function called per iteration.
3. `thisArg` *(Mixed)*: The `this` binding for the callback.

#### Returns
*(Array, Object)*: Returns the object iterated over.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkextenddestination--source"></a>`Benchmark.extend(destination [, source={}])`
<a href="#benchmarkextenddestination--source">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1446 "View in source") [&#x24C9;][1]

Copies enumerable properties from the source(s) object to the destination object.

#### Arguments
1. `destination` *(Object)*: The destination object.
2. `[source={}]` *(Object)*: The source object.

#### Returns
*(Object)*: The destination object.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkfilterarray-callback-thisarg"></a>`Benchmark.filter(array, callback, thisArg)`
<a href="#benchmarkfilterarray-callback-thisarg">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1485 "View in source") [&#x24C9;][1]

A generic `Array#filter` like method.

#### Arguments
1. `array` *(Array)*: The array to iterate over.
2. `callback` *(Function|String)*: The function/alias called per iteration.
3. `thisArg` *(Mixed)*: The `this` binding for the callback.

#### Returns
*(Array)*: A new array of values that passed callback filter.

#### Example
```js
// get odd numbers
Benchmark.filter([1, 2, 3, 4, 5], function(n) {
  return n % 2;
}); // -> [1, 3, 5];

// get fastest benchmarks
Benchmark.filter(benches, 'fastest');

// get slowest benchmarks
Benchmark.filter(benches, 'slowest');

// get benchmarks that completed without erroring
Benchmark.filter(benches, 'successful');
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkforeacharray-callback-thisarg"></a>`Benchmark.forEach(array, callback, thisArg)`
<a href="#benchmarkforeacharray-callback-thisarg">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1518 "View in source") [&#x24C9;][1]

A generic `Array#forEach` like method. Callbacks may terminate the loop by explicitly returning `false`.

#### Arguments
1. `array` *(Array)*: The array to iterate over.
2. `callback` *(Function)*: The function called per iteration.
3. `thisArg` *(Mixed)*: The `this` binding for the callback.

#### Returns
*(Array)*: Returns the array iterated over.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkformatnumbernumber"></a>`Benchmark.formatNumber(number)`
<a href="#benchmarkformatnumbernumber">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1557 "View in source") [&#x24C9;][1]

Converts a number to a more readable comma-separated string representation.

#### Arguments
1. `number` *(Number)*: The number to convert.

#### Returns
*(String)*: The more readable string representation.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkforownobject-callback-thisarg"></a>`Benchmark.forOwn(object, callback, thisArg)`
<a href="#benchmarkforownobject-callback-thisarg">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1545 "View in source") [&#x24C9;][1]

Iterates over an object's own properties, executing the `callback` for each. Callbacks may terminate the loop by explicitly returning `false`.

#### Arguments
1. `object` *(Object)*: The object to iterate over.
2. `callback` *(Function)*: The function executed per own property.
3. `thisArg` *(Mixed)*: The `this` binding for the callback.

#### Returns
*(Object)*: Returns the object iterated over.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkhaskeyobject-key"></a>`Benchmark.hasKey(object, key)`
<a href="#benchmarkhaskeyobject-key">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1572 "View in source") [&#x24C9;][1]

Checks if an object has the specified key as a direct property.

#### Arguments
1. `object` *(Object)*: The object to check.
2. `key` *(String)*: The key to check for.

#### Returns
*(Boolean)*: Returns `true` if key is a direct property, else `false`.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkindexofarray-value--fromindex0"></a>`Benchmark.indexOf(array, value [, fromIndex=0])`
<a href="#benchmarkindexofarray-value--fromindex0">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1608 "View in source") [&#x24C9;][1]

A generic `Array#indexOf` like method.

#### Arguments
1. `array` *(Array)*: The array to iterate over.
2. `value` *(Mixed)*: The value to search for.
3. `[fromIndex=0]` *(Number)*: The index to start searching from.

#### Returns
*(Number)*: The index of the matched value or `-1`.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkinterpolatestring-object"></a>`Benchmark.interpolate(string, object)`
<a href="#benchmarkinterpolatestring-object">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1630 "View in source") [&#x24C9;][1]

Modify a string by replacing named tokens with matching object property values.

#### Arguments
1. `string` *(String)*: The string to modify.
2. `object` *(Object)*: The template object.

#### Returns
*(String)*: The modified string.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkinvokebenches-name--arg1-arg2-"></a>`Benchmark.invoke(benches, name [, arg1, arg2, ...])`
<a href="#benchmarkinvokebenches-name--arg1-arg2-">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1677 "View in source") [&#x24C9;][1]

Invokes a method on all items in an array.

#### Arguments
1. `benches` *(Array)*: Array of benchmarks to iterate over.
2. `name` *(String|Object)*: The name of the method to invoke OR options object.
3. `[arg1, arg2, ...]` *(Mixed)*: Arguments to invoke the method with.

#### Returns
*(Array)*: A new array of values returned from each method invoked.

#### Example
```js
// invoke `reset` on all benchmarks
Benchmark.invoke(benches, 'reset');

// invoke `emit` with arguments
Benchmark.invoke(benches, 'emit', 'complete', listener);

// invoke `run(true)`, treat benchmarks as a queue, and register invoke callbacks
Benchmark.invoke(benches, {

  // invoke the `run` method
  'name': 'run',

  // pass a single argument
  'args': true,

  // treat as queue, removing benchmarks from front of `benches` until empty
  'queued': true,

  // called before any benchmarks have been invoked.
  'onStart': onStart,

  // called between invoking benchmarks
  'onCycle': onCycle,

  // called after all benchmarks have been invoked.
  'onComplete': onComplete
});
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkjoinobject--separator1--separator2:"></a>`Benchmark.join(object [, separator1=',', separator2=': '])`
<a href="#benchmarkjoinobject--separator1--separator2:">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1831 "View in source") [&#x24C9;][1]

Creates a string of joined array values or object key-value pairs.

#### Arguments
1. `object` *(Array|Object)*: The object to operate on.
2. `[separator1=',']` *(String)*: The separator used between key-value pairs.
3. `[separator2=': ']` *(String)*: The separator used between keys and values.

#### Returns
*(String)*: The joined result.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkmaparray-callback-thisarg"></a>`Benchmark.map(array, callback, thisArg)`
<a href="#benchmarkmaparray-callback-thisarg">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1853 "View in source") [&#x24C9;][1]

A generic `Array#map` like method.

#### Arguments
1. `array` *(Array)*: The array to iterate over.
2. `callback` *(Function)*: The function called per iteration.
3. `thisArg` *(Mixed)*: The `this` binding for the callback.

#### Returns
*(Array)*: A new array of values returned by the callback.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkpluckarray-property"></a>`Benchmark.pluck(array, property)`
<a href="#benchmarkpluckarray-property">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1869 "View in source") [&#x24C9;][1]

Retrieves the value of a specified property from all items in an array.

#### Arguments
1. `array` *(Array)*: The array to iterate over.
2. `property` *(String)*: The property to pluck.

#### Returns
*(Array)*: A new array of property values.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkreducearray-callback-accumulator"></a>`Benchmark.reduce(array, callback, accumulator)`
<a href="#benchmarkreducearray-callback-accumulator">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1885 "View in source") [&#x24C9;][1]

A generic `Array#reduce` like method.

#### Arguments
1. `array` *(Array)*: The array to iterate over.
2. `callback` *(Function)*: The function called per iteration.
3. `accumulator` *(Mixed)*: Initial value of the accumulator.

#### Returns
*(Mixed)*: The accumulator.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.prototype`

<!-- div -->

### <a id="benchmarkprototypeaborted"></a>`Benchmark.prototype.aborted`
<a href="#benchmarkprototypeaborted">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3378 "View in source") [&#x24C9;][1]

*(Boolean)*: A flag to indicate if the benchmark is aborted.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypecompiled"></a>`Benchmark.prototype.compiled`
<a href="#benchmarkprototypecompiled">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3354 "View in source") [&#x24C9;][1]

*(Function, String)*: The compiled test function.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypecount"></a>`Benchmark.prototype.count`
<a href="#benchmarkprototypecount">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3330 "View in source") [&#x24C9;][1]

*(Number)*: The number of times a test was executed.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypecycles"></a>`Benchmark.prototype.cycles`
<a href="#benchmarkprototypecycles">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3338 "View in source") [&#x24C9;][1]

*(Number)*: The number of cycles performed while benchmarking.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypefn"></a>`Benchmark.prototype.fn`
<a href="#benchmarkprototypefn">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3370 "View in source") [&#x24C9;][1]

*(Function, String)*: The test to benchmark.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypehz"></a>`Benchmark.prototype.hz`
<a href="#benchmarkprototypehz">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3346 "View in source") [&#x24C9;][1]

*(Number)*: The number of executions per second.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototyperunning"></a>`Benchmark.prototype.running`
<a href="#benchmarkprototyperunning">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3386 "View in source") [&#x24C9;][1]

*(Boolean)*: A flag to indicate if the benchmark is running.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypesetup"></a>`Benchmark.prototype.setup`
<a href="#benchmarkprototypesetup">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3449 "View in source") [&#x24C9;][1]

*(Function, String)*: Compiled into the test and executed immediately **before** the test loop.

#### Example
```js
// basic usage
var bench = Benchmark({
  'setup': function() {
    var c = this.count,
        element = document.getElementById('container');
    while (c--) {
      element.appendChild(document.createElement('div'));
    }
  },
  'fn': function() {
    element.removeChild(element.lastChild);
  }
});

// compiles to something like:
var c = this.count,
    element = document.getElementById('container');
while (c--) {
  element.appendChild(document.createElement('div'));
}
var start = new Date;
while (count--) {
  element.removeChild(element.lastChild);
}
var end = new Date - start;

// or using strings
var bench = Benchmark({
  'setup': '\
    var a = 0;\n\
    (function() {\n\
      (function() {\n\
        (function() {',
  'fn': 'a += 1;',
  'teardown': '\
         }())\n\
       }())\n\
     }())'
});

// compiles to something like:
var a = 0;
(function() {
  (function() {
    (function() {
      var start = new Date;
      while (count--) {
        a += 1;
      }
      var end = new Date - start;
    }())
  }())
}())
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypeteardown"></a>`Benchmark.prototype.teardown`
<a href="#benchmarkprototypeteardown">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3457 "View in source") [&#x24C9;][1]

*(Function, String)*: Compiled into the test and executed immediately **after** the test loop.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypeabort"></a>`Benchmark.prototype.abort()`
<a href="#benchmarkprototypeabort">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2218 "View in source") [&#x24C9;][1]

Aborts the benchmark without recording times.

#### Returns
*(Object)*: The benchmark instance.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypecloneoptions"></a>`Benchmark.prototype.clone(options)`
<a href="#benchmarkprototypecloneoptions">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2257 "View in source") [&#x24C9;][1]

Creates a new benchmark using the same test and options.

#### Arguments
1. `options` *(Object)*: Options object to overwrite cloned options.

#### Returns
*(Object)*: The new benchmark instance.

#### Example
```js
var bizarro = bench.clone({
  'name': 'doppelganger'
});
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypecompareother"></a>`Benchmark.prototype.compare(other)`
<a href="#benchmarkprototypecompareother">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2280 "View in source") [&#x24C9;][1]

Determines if a benchmark is faster than another.

#### Arguments
1. `other` *(Object)*: The benchmark to compare.

#### Returns
*(Number)*: Returns `-1` if slower, `1` if faster, and `0` if indeterminate.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypeemittype"></a>`Benchmark.Suite.prototype.emit(type)`
<a href="#benchmarkprototypeemittype">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2095 "View in source") [&#x24C9;][1]

Executes all registered listeners of the specified event type.

#### Arguments
1. `type` *(String|Object)*: The event type or object.

#### Returns
*(Mixed)*: Returns the return value of the last listener executed.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypelistenerstype"></a>`Benchmark.Suite.prototype.listeners(type)`
<a href="#benchmarkprototypelistenerstype">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2125 "View in source") [&#x24C9;][1]

Returns an array of event listeners for a given type that can be manipulated to add or remove listeners.

#### Arguments
1. `type` *(String)*: The event type.

#### Returns
*(Array)*: The listeners array.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypeofftype-listener"></a>`Benchmark.Suite.prototype.off([type, listener])`
<a href="#benchmarkprototypeofftype-listener">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2158 "View in source") [&#x24C9;][1]

Unregisters a listener for the specified event type(s), or unregisters all listeners for the specified event type(s), or unregisters all listeners for all event types.

#### Arguments
1. `[type]` *(String)*: The event type.
2. `[listener]` *(Function)*: The function to unregister.

#### Returns
*(Object)*: The benchmark instance.

#### Example
```js
// unregister a listener for an event type
bench.off('cycle', listener);

// unregister a listener for multiple event types
bench.off('start cycle', listener);

// unregister all listeners for an event type
bench.off('cycle');

// unregister all listeners for multiple event types
bench.off('start cycle complete');

// unregister all listeners for all event types
bench.off();
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypeontype-listener"></a>`Benchmark.Suite.prototype.on(type, listener)`
<a href="#benchmarkprototypeontype-listener">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2197 "View in source") [&#x24C9;][1]

Registers a listener for the specified event type(s).

#### Arguments
1. `type` *(String)*: The event type.
2. `listener` *(Function)*: The function to register.

#### Returns
*(Object)*: The benchmark instance.

#### Example
```js
// register a listener for an event type
bench.on('cycle', listener);

// register a listener for multiple event types
bench.on('start cycle', listener);
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypereset"></a>`Benchmark.prototype.reset()`
<a href="#benchmarkprototypereset">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2334 "View in source") [&#x24C9;][1]

Reset properties and abort if running.

#### Returns
*(Object)*: The benchmark instance.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototyperunoptions"></a>`Benchmark.prototype.run([options={}])`
<a href="#benchmarkprototyperunoptions">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3000 "View in source") [&#x24C9;][1]

Runs the benchmark.

#### Arguments
1. `[options={}]` *(Object)*: Options object.

#### Returns
*(Object)*: The benchmark instance.

#### Example
```js
// basic usage
bench.run();

// or with options
bench.run({ 'async': true });
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypetostring"></a>`Benchmark.prototype.toString()`
<a href="#benchmarkprototypetostring">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2405 "View in source") [&#x24C9;][1]

Displays relevant benchmark information when coerced to a string.

#### Returns
*(String)*: A string representation of the benchmark instance.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.options`

<!-- div -->

### <a id="benchmarkoptions"></a>`Benchmark.options`
<a href="#benchmarkoptions">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3049 "View in source") [&#x24C9;][1]

*(Object)*: The default options copied by benchmark instances.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsasync"></a>`Benchmark.options.async`
<a href="#benchmarkoptionsasync">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3058 "View in source") [&#x24C9;][1]

*(Boolean)*: A flag to indicate that benchmark cycles will execute asynchronously by default.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsdefer"></a>`Benchmark.options.defer`
<a href="#benchmarkoptionsdefer">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3066 "View in source") [&#x24C9;][1]

*(Boolean)*: A flag to indicate that the benchmark clock is deferred.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsdelay"></a>`Benchmark.options.delay`
<a href="#benchmarkoptionsdelay">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3073 "View in source") [&#x24C9;][1]

*(Number)*: The delay between test cycles *(secs)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsid"></a>`Benchmark.options.id`
<a href="#benchmarkoptionsid">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3082 "View in source") [&#x24C9;][1]

*(String)*: Displayed by Benchmark#toString when a `name` is not available *(auto-generated if absent)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsinitcount"></a>`Benchmark.options.initCount`
<a href="#benchmarkoptionsinitcount">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3090 "View in source") [&#x24C9;][1]

*(Number)*: The default number of times to execute a test on a benchmark's first cycle.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsmaxtime"></a>`Benchmark.options.maxTime`
<a href="#benchmarkoptionsmaxtime">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3100 "View in source") [&#x24C9;][1]

*(Number)*: The maximum time a benchmark is allowed to run before finishing *(secs)*.  Note: Cycle delays aren't counted toward the maximum time.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsminsamples"></a>`Benchmark.options.minSamples`
<a href="#benchmarkoptionsminsamples">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3108 "View in source") [&#x24C9;][1]

*(Number)*: The minimum sample size required to perform statistical analysis.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsmintime"></a>`Benchmark.options.minTime`
<a href="#benchmarkoptionsmintime">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3116 "View in source") [&#x24C9;][1]

*(Number)*: The time needed to reduce the percent uncertainty of measurement to `1`% *(secs)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsname"></a>`Benchmark.options.name`
<a href="#benchmarkoptionsname">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3124 "View in source") [&#x24C9;][1]

*(String)*: The name of the benchmark.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsonabort"></a>`Benchmark.options.onAbort`
<a href="#benchmarkoptionsonabort">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3132 "View in source") [&#x24C9;][1]

An event listener called when the benchmark is aborted.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsoncomplete"></a>`Benchmark.options.onComplete`
<a href="#benchmarkoptionsoncomplete">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3140 "View in source") [&#x24C9;][1]

An event listener called when the benchmark completes running.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsoncycle"></a>`Benchmark.options.onCycle`
<a href="#benchmarkoptionsoncycle">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3148 "View in source") [&#x24C9;][1]

An event listener called after each run cycle.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsonerror"></a>`Benchmark.options.onError`
<a href="#benchmarkoptionsonerror">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3156 "View in source") [&#x24C9;][1]

An event listener called when a test errors.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsonreset"></a>`Benchmark.options.onReset`
<a href="#benchmarkoptionsonreset">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3164 "View in source") [&#x24C9;][1]

An event listener called when the benchmark is reset.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkoptionsonstart"></a>`Benchmark.options.onStart`
<a href="#benchmarkoptionsonstart">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3172 "View in source") [&#x24C9;][1]

An event listener called when the benchmark starts running.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.platform`

<!-- div -->

### <a id="benchmarkplatform"></a>`Benchmark.platform`
<a href="#benchmarkplatform">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3183 "View in source") [&#x24C9;][1]

*(Object)*: Platform object with properties describing things like browser name, version, and operating system.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformdescription"></a>`Benchmark.platform.description`
<a href="#benchmarkplatformdescription">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3191 "View in source") [&#x24C9;][1]

*(String)*: The platform description.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformlayout"></a>`Benchmark.platform.layout`
<a href="#benchmarkplatformlayout">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3199 "View in source") [&#x24C9;][1]

*(String, Null)*: The name of the browser layout engine.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformmanufacturer"></a>`Benchmark.platform.manufacturer`
<a href="#benchmarkplatformmanufacturer">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3223 "View in source") [&#x24C9;][1]

*(String, Null)*: The name of the product's manufacturer.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformname"></a>`Benchmark.platform.name`
<a href="#benchmarkplatformname">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3215 "View in source") [&#x24C9;][1]

*(String, Null)*: The name of the browser/environment.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformos"></a>`Benchmark.platform.os`
<a href="#benchmarkplatformos">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3231 "View in source") [&#x24C9;][1]

*(String, Null)*: The name of the operating system.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformprerelease"></a>`Benchmark.platform.prerelease`
<a href="#benchmarkplatformprerelease">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3239 "View in source") [&#x24C9;][1]

*(String, Null)*: The alpha/beta release indicator.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformproduct"></a>`Benchmark.platform.product`
<a href="#benchmarkplatformproduct">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3207 "View in source") [&#x24C9;][1]

*(String, Null)*: The name of the product hosting the browser.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformversion"></a>`Benchmark.platform.version`
<a href="#benchmarkplatformversion">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3247 "View in source") [&#x24C9;][1]

*(String, Null)*: The browser/environment version.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkplatformtostring"></a>`Benchmark.platform.toString()`
<a href="#benchmarkplatformtostring">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3256 "View in source") [&#x24C9;][1]

Return platform description when the platform object is coerced to a string.

#### Returns
*(String)*: The platform description.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.support`

<!-- div -->

### <a id="benchmarksupport"></a>`Benchmark.support`
<a href="#benchmarksupport">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L135 "View in source") [&#x24C9;][1]

*(Object)*: An object used to flag environments/features.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportair"></a>`Benchmark.support.air`
<a href="#benchmarksupportair">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L145 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect Adobe AIR.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportargumentsclass"></a>`Benchmark.support.argumentsClass`
<a href="#benchmarksupportargumentsclass">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L153 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if `arguments` objects have the correct internal [[Class]] value.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportbrowser"></a>`Benchmark.support.browser`
<a href="#benchmarksupportbrowser">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L161 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if in a browser environment.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportcharbyindex"></a>`Benchmark.support.charByIndex`
<a href="#benchmarksupportcharbyindex">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L169 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if strings support accessing characters by index.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportcharbyownindex"></a>`Benchmark.support.charByOwnIndex`
<a href="#benchmarksupportcharbyownindex">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L179 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if strings have indexes as own properties.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportdecompilation"></a>`Benchmark.support.decompilation`
<a href="#benchmarksupportdecompilation">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L207 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if functions support decompilation.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportdescriptors"></a>`Benchmark.support.descriptors`
<a href="#benchmarksupportdescriptors">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L228 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect ES5+ property descriptor API.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportgetallkeys"></a>`Benchmark.support.getAllKeys`
<a href="#benchmarksupportgetallkeys">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L242 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect ES5+ Object.getOwnPropertyNames().

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportiteratesownfirst"></a>`Benchmark.support.iteratesOwnFirst`
<a href="#benchmarksupportiteratesownfirst">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L255 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if own properties are iterated before inherited properties *(all but IE < `9`)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportjava"></a>`Benchmark.support.java`
<a href="#benchmarksupportjava">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L190 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if Java is enabled/exposed.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupportnodeclass"></a>`Benchmark.support.nodeClass`
<a href="#benchmarksupportnodeclass">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L272 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if a node's [[Class]] is resolvable *(all but IE < `9`)* and that the JS engine errors when attempting to coerce an object to a string without a `toString` property value of `typeof` "function".

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksupporttimeout"></a>`Benchmark.support.timeout`
<a href="#benchmarksupporttimeout">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L198 "View in source") [&#x24C9;][1]

*(Boolean)*: Detect if the Timers API exists.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.prototype.error`

<!-- div -->

### <a id="benchmarkprototypeerror"></a>`Benchmark.prototype.error`
<a href="#benchmarkprototypeerror">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3362 "View in source") [&#x24C9;][1]

*(Object)*: The error object if the test failed.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.prototype.stats`

<!-- div -->

### <a id="benchmarkprototypestats"></a>`Benchmark.prototype.stats`
<a href="#benchmarkprototypestats">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3465 "View in source") [&#x24C9;][1]

*(Object)*: An object of stats including mean, margin or error, and standard deviation.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-statsdeviation"></a>`Benchmark.prototype.stats.deviation`
<a href="#benchmark-statsdeviation">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3497 "View in source") [&#x24C9;][1]

*(Number)*: The sample standard deviation.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-statsmean"></a>`Benchmark.prototype.stats.mean`
<a href="#benchmark-statsmean">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3505 "View in source") [&#x24C9;][1]

*(Number)*: The sample arithmetic mean.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-statsmoe"></a>`Benchmark.prototype.stats.moe`
<a href="#benchmark-statsmoe">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3473 "View in source") [&#x24C9;][1]

*(Number)*: The margin of error.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-statsrme"></a>`Benchmark.prototype.stats.rme`
<a href="#benchmark-statsrme">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3481 "View in source") [&#x24C9;][1]

*(Number)*: The relative margin of error *(expressed as a percentage of the mean)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-statssample"></a>`Benchmark.prototype.stats.sample`
<a href="#benchmark-statssample">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3513 "View in source") [&#x24C9;][1]

*(Array)*: The array of sampled periods.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-statssem"></a>`Benchmark.prototype.stats.sem`
<a href="#benchmark-statssem">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3489 "View in source") [&#x24C9;][1]

*(Number)*: The standard error of the mean.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-statsvariance"></a>`Benchmark.prototype.stats.variance`
<a href="#benchmark-statsvariance">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3521 "View in source") [&#x24C9;][1]

*(Number)*: The sample variance.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.prototype.times`

<!-- div -->

### <a id="benchmarkprototypetimes"></a>`Benchmark.prototype.times`
<a href="#benchmarkprototypetimes">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3530 "View in source") [&#x24C9;][1]

*(Object)*: An object of timing data including cycle, elapsed, period, start, and stop.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-timescycle"></a>`Benchmark.prototype.times.cycle`
<a href="#benchmark-timescycle">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3538 "View in source") [&#x24C9;][1]

*(Number)*: The time taken to complete the last cycle *(secs)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-timeselapsed"></a>`Benchmark.prototype.times.elapsed`
<a href="#benchmark-timeselapsed">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3546 "View in source") [&#x24C9;][1]

*(Number)*: The time taken to complete the benchmark *(secs)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-timesperiod"></a>`Benchmark.prototype.times.period`
<a href="#benchmark-timesperiod">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3554 "View in source") [&#x24C9;][1]

*(Number)*: The time taken to execute the test once *(secs)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmark-timestimestamp"></a>`Benchmark.prototype.times.timeStamp`
<a href="#benchmark-timestimestamp">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3562 "View in source") [&#x24C9;][1]

*(Number)*: A timestamp of when the benchmark started *(ms)*.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Deferred`

<!-- div -->

### <a id="benchmarkdeferredclone"></a>`Benchmark.Deferred(clone)`
<a href="#benchmarkdeferredclone">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L445 "View in source") [&#x24C9;][1]

The Deferred constructor.

#### Arguments
1. `clone` *(Object)*: The cloned benchmark instance.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Deferred.prototype`

<!-- div -->

### <a id="benchmarkdeferredprototypebenchmark"></a>`Benchmark.Deferred.prototype.benchmark`
<a href="#benchmarkdeferredprototypebenchmark">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3606 "View in source") [&#x24C9;][1]

*(Object)*: The deferred benchmark instance.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkdeferredprototypecycles"></a>`Benchmark.Deferred.prototype.cycles`
<a href="#benchmarkdeferredprototypecycles">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3614 "View in source") [&#x24C9;][1]

*(Number)*: The number of deferred cycles performed while benchmarking.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkdeferredprototypeelapsed"></a>`Benchmark.Deferred.prototype.elapsed`
<a href="#benchmarkdeferredprototypeelapsed">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3622 "View in source") [&#x24C9;][1]

*(Number)*: The time taken to complete the deferred benchmark *(secs)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkdeferredprototyperesolve"></a>`Benchmark.Deferred.prototype.resolve`
<a href="#benchmarkdeferredprototyperesolve">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1188 "View in source") [&#x24C9;][1]

*(Unknown)*: Handles cycling/completing the deferred benchmark.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkdeferredprototypetimestamp"></a>`Benchmark.Deferred.prototype.timeStamp`
<a href="#benchmarkdeferredprototypetimestamp">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3630 "View in source") [&#x24C9;][1]

*(Number)*: A timestamp of when the deferred benchmark started *(ms)*.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Event`

<!-- div -->

### <a id="benchmarkeventtype"></a>`Benchmark.Event(type)`
<a href="#benchmarkeventtype">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L461 "View in source") [&#x24C9;][1]

The Event constructor.

#### Arguments
1. `type` *(String|Object)*: The event type.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Event.prototype`

<!-- div -->

### <a id="benchmarkeventprototypeaborted"></a>`Benchmark.Event.prototype.aborted`
<a href="#benchmarkeventprototypeaborted">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3646 "View in source") [&#x24C9;][1]

*(Boolean)*: A flag to indicate if the emitters listener iteration is aborted.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkeventprototypecancelled"></a>`Benchmark.Event.prototype.cancelled`
<a href="#benchmarkeventprototypecancelled">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3654 "View in source") [&#x24C9;][1]

*(Boolean)*: A flag to indicate if the default action is cancelled.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkeventprototyperesult"></a>`Benchmark.Event.prototype.result`
<a href="#benchmarkeventprototyperesult">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3670 "View in source") [&#x24C9;][1]

*(Mixed)*: The return value of the last executed listener.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkeventprototypetimestamp"></a>`Benchmark.Event.prototype.timeStamp`
<a href="#benchmarkeventprototypetimestamp">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3686 "View in source") [&#x24C9;][1]

*(Number)*: A timestamp of when the event was created *(ms)*.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkeventprototypetype"></a>`Benchmark.Event.prototype.type`
<a href="#benchmarkeventprototypetype">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3694 "View in source") [&#x24C9;][1]

*(String)*: The event type.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Event.prototype.currentTarget`

<!-- div -->

### <a id="benchmarkeventprototypecurrenttarget"></a>`Benchmark.Event.prototype.currentTarget`
<a href="#benchmarkeventprototypecurrenttarget">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3662 "View in source") [&#x24C9;][1]

*(Object)*: The object whose listeners are currently being processed.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Event.prototype.target`

<!-- div -->

### <a id="benchmarkeventprototypetarget"></a>`Benchmark.Event.prototype.target`
<a href="#benchmarkeventprototypetarget">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3678 "View in source") [&#x24C9;][1]

*(Object)*: The object to which the event was originally emitted.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Suite`

<!-- div -->

### <a id="benchmarksuitename--options"></a>`Benchmark.Suite(name [, options={}])`
<a href="#benchmarksuitename--options">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L507 "View in source") [&#x24C9;][1]

The Suite constructor.

#### Arguments
1. `name` *(String)*: A name to identify the suite.
2. `[options={}]` *(Object)*: Options object.

#### Example
```js
// basic usage (the `new` operator is optional)
var suite = new Benchmark.Suite;

// or using a name first
var suite = new Benchmark.Suite('foo');

// or with options
var suite = new Benchmark.Suite('foo', {

  // called when the suite starts running
  'onStart': onStart,

  // called between running benchmarks
  'onCycle': onCycle,

  // called when aborted
  'onAbort': onAbort,

  // called when a test errors
  'onError': onError,

  // called when reset
  'onReset': onReset,

  // called when the suite completes running
  'onComplete': onComplete
});
```

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Suite.prototype`

<!-- div -->

### <a id="benchmarksuiteprototypeaborted"></a>`Benchmark.Suite.prototype.aborted`
<a href="#benchmarksuiteprototypeaborted">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3735 "View in source") [&#x24C9;][1]

*(Boolean)*: A flag to indicate if the suite is aborted.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypelength"></a>`Benchmark.Suite.prototype.length`
<a href="#benchmarksuiteprototypelength">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3727 "View in source") [&#x24C9;][1]

*(Number)*: The number of benchmarks in the suite.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototyperunning"></a>`Benchmark.Suite.prototype.running`
<a href="#benchmarksuiteprototyperunning">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3743 "View in source") [&#x24C9;][1]

*(Boolean)*: A flag to indicate if the suite is running.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypeabort"></a>`Benchmark.Suite.prototype.abort()`
<a href="#benchmarksuiteprototypeabort">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1902 "View in source") [&#x24C9;][1]

Aborts all benchmarks in the suite.

#### Returns
*(Object)*: The suite instance.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypeaddname-fn--options"></a>`Benchmark.Suite.prototype.add(name, fn [, options={}])`
<a href="#benchmarksuiteprototypeaddname-fn--options">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1962 "View in source") [&#x24C9;][1]

Adds a test to the benchmark suite.

#### Arguments
1. `name` *(String)*: A name to identify the benchmark.
2. `fn` *(Function|String)*: The test to benchmark.
3. `[options={}]` *(Object)*: Options object.

#### Returns
*(Object)*: The benchmark instance.

#### Example
```js
// basic usage
suite.add(fn);

// or using a name first
suite.add('foo', fn);

// or with options
suite.add('foo', fn, {
  'onCycle': onCycle,
  'onComplete': onComplete
});

// or name and options
suite.add('foo', {
  'fn': fn,
  'onCycle': onCycle,
  'onComplete': onComplete
});

// or options only
suite.add({
  'name': 'foo',
  'fn': fn,
  'onCycle': onCycle,
  'onComplete': onComplete
});
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypecloneoptions"></a>`Benchmark.Suite.prototype.clone(options)`
<a href="#benchmarksuiteprototypecloneoptions">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L1981 "View in source") [&#x24C9;][1]

Creates a new suite with cloned benchmarks.

#### Arguments
1. `options` *(Object)*: Options object to overwrite cloned options.

#### Returns
*(Object)*: The new suite instance.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypeemittype"></a>`Benchmark.Suite.prototype.emit(type)`
<a href="#benchmarkprototypeemittype">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2095 "View in source") [&#x24C9;][1]

Executes all registered listeners of the specified event type.

#### Arguments
1. `type` *(String|Object)*: The event type or object.

#### Returns
*(Mixed)*: Returns the return value of the last listener executed.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypefiltercallback"></a>`Benchmark.Suite.prototype.filter(callback)`
<a href="#benchmarksuiteprototypefiltercallback">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2004 "View in source") [&#x24C9;][1]

An `Array#filter` like method.

#### Arguments
1. `callback` *(Function|String)*: The function/alias called per iteration.

#### Returns
*(Object)*: A new suite of benchmarks that passed callback filter.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypeforeachcallback"></a>`Benchmark.Suite.prototype.forEach(callback)`
<a href="#benchmarksuiteprototypeforeachcallback">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3753 "View in source") [&#x24C9;][1]

An `Array#forEach` like method. Callbacks may terminate the loop by explicitly returning `false`.

#### Arguments
1. `callback` *(Function)*: The function called per iteration.

#### Returns
*(Object)*: The suite iterated over.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypeindexofvalue"></a>`Benchmark.Suite.prototype.indexOf(value)`
<a href="#benchmarksuiteprototypeindexofvalue">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3762 "View in source") [&#x24C9;][1]

An `Array#indexOf` like method.

#### Arguments
1. `value` *(Mixed)*: The value to search for.

#### Returns
*(Number)*: The index of the matched value or `-1`.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypeinvokename--arg1-arg2-"></a>`Benchmark.Suite.prototype.invoke(name [, arg1, arg2, ...])`
<a href="#benchmarksuiteprototypeinvokename--arg1-arg2-">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3772 "View in source") [&#x24C9;][1]

Invokes a method on all benchmarks in the suite.

#### Arguments
1. `name` *(String|Object)*: The name of the method to invoke OR options object.
2. `[arg1, arg2, ...]` *(Mixed)*: Arguments to invoke the method with.

#### Returns
*(Array)*: A new array of values returned from each method invoked.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypejoinseparator-"></a>`Benchmark.Suite.prototype.join([separator=','])`
<a href="#benchmarksuiteprototypejoinseparator-">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3781 "View in source") [&#x24C9;][1]

Converts the suite of benchmarks to a string.

#### Arguments
1. `[separator=',']` *(String)*: A string to separate each element of the array.

#### Returns
*(String)*: The string.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypelistenerstype"></a>`Benchmark.Suite.prototype.listeners(type)`
<a href="#benchmarkprototypelistenerstype">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2125 "View in source") [&#x24C9;][1]

Returns an array of event listeners for a given type that can be manipulated to add or remove listeners.

#### Arguments
1. `type` *(String)*: The event type.

#### Returns
*(Array)*: The listeners array.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypemapcallback"></a>`Benchmark.Suite.prototype.map(callback)`
<a href="#benchmarksuiteprototypemapcallback">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3790 "View in source") [&#x24C9;][1]

An `Array#map` like method.

#### Arguments
1. `callback` *(Function)*: The function called per iteration.

#### Returns
*(Array)*: A new array of values returned by the callback.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypeofftype-listener"></a>`Benchmark.Suite.prototype.off([type, listener])`
<a href="#benchmarkprototypeofftype-listener">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2158 "View in source") [&#x24C9;][1]

Unregisters a listener for the specified event type(s), or unregisters all listeners for the specified event type(s), or unregisters all listeners for all event types.

#### Arguments
1. `[type]` *(String)*: The event type.
2. `[listener]` *(Function)*: The function to unregister.

#### Returns
*(Object)*: The benchmark instance.

#### Example
```js
// unregister a listener for an event type
bench.off('cycle', listener);

// unregister a listener for multiple event types
bench.off('start cycle', listener);

// unregister all listeners for an event type
bench.off('cycle');

// unregister all listeners for multiple event types
bench.off('start cycle complete');

// unregister all listeners for all event types
bench.off();
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarkprototypeontype-listener"></a>`Benchmark.Suite.prototype.on(type, listener)`
<a href="#benchmarkprototypeontype-listener">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2197 "View in source") [&#x24C9;][1]

Registers a listener for the specified event type(s).

#### Arguments
1. `type` *(String)*: The event type.
2. `listener` *(Function)*: The function to register.

#### Returns
*(Object)*: The benchmark instance.

#### Example
```js
// register a listener for an event type
bench.on('cycle', listener);

// register a listener for multiple event types
bench.on('start cycle', listener);
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypepluckproperty"></a>`Benchmark.Suite.prototype.pluck(property)`
<a href="#benchmarksuiteprototypepluckproperty">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3799 "View in source") [&#x24C9;][1]

Retrieves the value of a specified property from all benchmarks in the suite.

#### Arguments
1. `property` *(String)*: The property to pluck.

#### Returns
*(Array)*: A new array of property values.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypepop"></a>`Benchmark.Suite.prototype.pop()`
<a href="#benchmarksuiteprototypepop">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3807 "View in source") [&#x24C9;][1]

Removes the last benchmark from the suite and returns it.

#### Returns
*(Mixed)*: The removed benchmark.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypepush"></a>`Benchmark.Suite.prototype.push()`
<a href="#benchmarksuiteprototypepush">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3815 "View in source") [&#x24C9;][1]

Appends benchmarks to the suite.

#### Returns
*(Number)*: The suite's new length.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypereducecallback-accumulator"></a>`Benchmark.Suite.prototype.reduce(callback, accumulator)`
<a href="#benchmarksuiteprototypereducecallback-accumulator">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3834 "View in source") [&#x24C9;][1]

An `Array#reduce` like method.

#### Arguments
1. `callback` *(Function)*: The function called per iteration.
2. `accumulator` *(Mixed)*: Initial value of the accumulator.

#### Returns
*(Mixed)*: The accumulator.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypereset"></a>`Benchmark.Suite.prototype.reset()`
<a href="#benchmarksuiteprototypereset">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2019 "View in source") [&#x24C9;][1]

Resets all benchmarks in the suite.

#### Returns
*(Object)*: The suite instance.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypereverse"></a>`Benchmark.Suite.prototype.reverse()`
<a href="#benchmarksuiteprototypereverse">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L638 "View in source") [&#x24C9;][1]

Rearrange the host array's elements in reverse order.

#### Returns
*(Array)*: The reversed array.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototyperunoptions"></a>`Benchmark.Suite.prototype.run([options={}])`
<a href="#benchmarksuiteprototyperunoptions">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L2056 "View in source") [&#x24C9;][1]

Runs the suite.

#### Arguments
1. `[options={}]` *(Object)*: Options object.

#### Returns
*(Object)*: The suite instance.

#### Example
```js
// basic usage
suite.run();

// or with options
suite.run({ 'async': true, 'queued': true });
```

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypeshift"></a>`Benchmark.Suite.prototype.shift()`
<a href="#benchmarksuiteprototypeshift">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L671 "View in source") [&#x24C9;][1]

Removes the first element of the host array and returns it.

#### Returns
*(Mixed)*: The first element of the array.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypeslicestart-end"></a>`Benchmark.Suite.prototype.slice(start, end)`
<a href="#benchmarksuiteprototypeslicestart-end">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L684 "View in source") [&#x24C9;][1]

Creates an array of the host array's elements from the start index up to, but not including, the end index.

#### Arguments
1. `start` *(Number)*: The starting index.
2. `end` *(Number)*: The end index.

#### Returns
*(Array)*: The new array.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypesortcomparefnnull"></a>`Benchmark.Suite.prototype.sort([compareFn=null])`
<a href="#benchmarksuiteprototypesortcomparefnnull">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3824 "View in source") [&#x24C9;][1]

Sorts the benchmarks of the suite.

#### Arguments
1. `[compareFn=null]` *(Function)*: A function that defines the sort order.

#### Returns
*(Object)*: The sorted suite.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypesplicestart-deletecount--val1-val2-"></a>`Benchmark.Suite.prototype.splice(start, deleteCount [, val1, val2, ...])`
<a href="#benchmarksuiteprototypesplicestart-deletecount--val1-val2-">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L714 "View in source") [&#x24C9;][1]

Allows removing a range of elements and/or inserting elements into the host array.

#### Arguments
1. `start` *(Number)*: The start index.
2. `deleteCount` *(Number)*: The number of elements to delete.
3. `[val1, val2, ...]` *(Mixed)*: values to insert at the `start` index.

#### Returns
*(Array)*: An array of removed elements.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteprototypeunshift"></a>`Benchmark.Suite.prototype.unshift()`
<a href="#benchmarksuiteprototypeunshift">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L749 "View in source") [&#x24C9;][1]

Appends arguments to the host array.

#### Returns
*(Number)*: The new length.

* * *

<!-- /div -->


<!-- /div -->


<!-- div -->

## `Benchmark.Suite.options`

<!-- div -->

### <a id="benchmarksuiteoptions"></a>`Benchmark.Suite.options`
<a href="#benchmarksuiteoptions">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3706 "View in source") [&#x24C9;][1]

*(Object)*: The default options copied by suite instances.

* * *

<!-- /div -->


<!-- div -->

### <a id="benchmarksuiteoptionsname"></a>`Benchmark.Suite.options.name`
<a href="#benchmarksuiteoptionsname">#</a> [&#x24C8;](https://github.com/bestiejs/benchmark.js/blob/master/benchmark.js#L3714 "View in source") [&#x24C9;][1]

*(String)*: The name of the suite.

* * *

<!-- /div -->


<!-- /div -->


<!-- /div -->


  [1]: #Benchmark "Jump back to the TOC."