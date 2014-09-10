# Benchmark.js runner [(demo)](http://rstacruz.github.io/benchmarkjs-runner/example.html)

Easy way to create performance tests for browser JS performance using 
[Benchmark.js]. Think of it like an easy-to-use version of [jsperf.com].

![Screenshot](http://rstacruz.github.io/benchmarkjs-runner/support/screenshot.png?v=0852)

## Usage

Simply create a plain HTML file that includes the `benchmark-runner` script,
like below. Also see [example.html](example.html) for more detailed
examples.

~~~ html
<!DOCTYPE html>
<meta charset='utf-8' />
<title>Benchmarks</title>
<script src='http://rstacruz.github.io/benchmarkjs-runner/runner.js'></script>
<script>

  suite("String matching", function() {
    bench("String#indexOf", function() {
      "Hello world".indexOf('o') > -1;
    });

    bench("String#match", function() {
      !! "Hello world".match(/o/);
    });

    bench("RegExp#test", function() {
      !! /o/.test("Hello world");
    });
  });

</script>
~~~

## API

* `suite(name, [options], function)` -- Defines a Benchmark suite. You may
optionally pass *options* to be used by Benchmark.js.

* `bench(name, function, [options])` -- Defines a Benchmark. You may optionally
pass *options* to be used by Benchmark.js.

* `afterEach(function)` -- Defines a function to be called after each benchmark
cycle. These routines do not contribute to the elapsed time of the benchmarks.

* `before(function)` -- Defines a function to be called *before* all benchmarks in
the suite are to be invoked. These routines do not contribute to the elapsed
time of the benchmarks.

* `after(function)` -- Defines a function to be called *after* all benchmarks in
the suite are invoked.

## Acknowledgements

Disclaimer: hastily cobbled together out of a need. Expect support to be sparse.

© 2013, Rico Sta. Cruz. Released under the [MIT License].

[MIT License]: http://www.opensource.org/licenses/mit-license.php
[jsperf.com]: http://jsperf.com/
[benchmark.js]: http://benchmarkjs.com/
