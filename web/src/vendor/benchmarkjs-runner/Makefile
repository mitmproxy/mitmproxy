runner.js: \
	bower_components/jquery/jquery.js \
	bower_components/benchmark/benchmark.js \
	src/runner.js
	cat $^ > $@

bower_components/jquery/jquery.js: bower_components
bower_components/benchmark/benchmark.js: bower_components

bower_components: bower.json
	bower install
	touch bower_components
