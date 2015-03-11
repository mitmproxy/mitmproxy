var path = require('path');

var packagejs = require('./package.json');
var conf = require('./conf.js');

// Sorted alphabetically!
var browserify = require('browserify');
var gulp = require("gulp");
var concat = require('gulp-concat');
var connect = require('gulp-connect');
var jshint = require("gulp-jshint");
var less = require("gulp-less");
var livereload = require("gulp-livereload");
var minifyCSS = require('gulp-minify-css');
var notify = require("gulp-notify");
var peg = require("gulp-peg");
var plumber = require("gulp-plumber");
var react = require("gulp-react");
var rename = require("gulp-rename");
var replace = require('gulp-replace');
var rev = require("gulp-rev");
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');
var _ = require('lodash');
var map = require("map-stream");
var reactify = require('reactify');
var buffer = require('vinyl-buffer');
var source = require('vinyl-source-stream');
var transform = require('vinyl-transform');

// FIXME: react-with-addons.min.js for prod use issue
// FIXME: Sourcemap URLs don't work correctly.
// FIXME: Why don't we use gulp-rev's manifest feature?

var manifest = {
    "vendor.css": "vendor.css",
    "app.css": "app.css",
    "vendor.js": "vendor.js",
    "app.js": "app.js",
};

var vendor_packages = _.difference(
    _.union(
        _.keys(packagejs.dependencies),
        conf.js.vendor_includes
    ),
    conf.js.vendor_excludes
);


// Custom linting reporter used for error notify
var jsHintErrorReporter = function(){
    return map(function (file, cb) {
        if (file.jshint && !file.jshint.success) {
            file.jshint.results.forEach(function (err) {
                if (err) {
                    var msg = [
                        path.basename(file.path),
                        'Line: ' + err.error.line,
                        'Reason: ' + err.error.reason
                    ];
                    notify.onError(
                        "Error: <%= error.message %>"
                    )(new Error(msg.join("\n")));
                }
            });
        }
        cb(null, file);
    })
};

function save_rev(){
    return map(function(file, callback){
        if (file.revOrigBase){
            manifest[path.basename(file.revOrigPath)] = path.basename(file.path);
        }
        callback(null, file);
    })
}

var dont_break_on_errors = function(){
    return plumber(
        function(error){
            notify.onError("Error: <%= error.message %>").apply(this, arguments);
            this.emit('end');
        }
    );
};

/*
 * Sourcemaps are a wonderful way to develop directly from the chrome devtools.
 * However, generating correct sourcemaps is a huge PITA, especially on Windows.
 * Fixing this upstream is tedious as apparently nobody really cares and
 * a single misbehaving transform breaks everything.
 * Thus, we just manually fix all paths.
 */
//Normalize \ to / on Windows.
function unixStylePath(filePath) {
  return filePath.split(path.sep).join('/');
}
// Hijack the sourceRoot attr to do our transforms
function fixSourceMapPaths(file){
    file.sourceMap.sources = file.sourceMap.sources.map(function (x) {
        return unixStylePath(path.relative(".", x));
    });
    return "/";
}
// Browserify fails for paths starting with "..".
function fixBrowserifySourceMapPaths(file){
    file.sourceMap.sources = file.sourceMap.sources.map(function (x) {
        return x.replace("src/js/node_modules","node_modules");
    });
    return fixSourceMapPaths(file);
}

gulp.task("fonts", function () {
    return gulp.src(conf.fonts)
        .pipe(gulp.dest(conf.static + "/fonts"))
});

function styles_dev(files) {
    return (gulp.src(files)
        .pipe(dont_break_on_errors())
        .pipe(sourcemaps.init())
        .pipe(less())
        .pipe(sourcemaps.write(".", {sourceRoot: fixSourceMapPaths}))
        .pipe(gulp.dest(conf.static))
        .pipe(livereload({ auto: false })));
}
gulp.task("styles-app-dev", function(){
    styles_dev(conf.css.app);
});
gulp.task("styles-vendor-dev", function(){
    styles_dev(conf.css.vendor);
});


function styles_prod(files) {
    return (gulp.src(files)
        .pipe(less())
        .pipe(minifyCSS())
        .pipe(rev())
        .pipe(save_rev())
        .pipe(gulp.dest(conf.static))
        .pipe(livereload({ auto: false })));
}
gulp.task("styles-app-prod", function(){
    styles_prod(conf.css.app);
});
gulp.task("styles-vendor-prod", function(){
    styles_prod(conf.css.vendor);
});


function vendor_stream(debug){
    var vendor = browserify(vendor_packages, {debug: debug});
    _.each(vendor_packages, function(v){
        vendor.require(v);
    });
    return vendor.bundle()
        .pipe(source("dummy.js"))
        .pipe(rename("vendor.js"));
}
gulp.task("scripts-vendor-dev", function (){
    return vendor_stream(false)
        .pipe(gulp.dest(conf.static));
});
gulp.task("scripts-vendor-prod", function(){
    return vendor_stream(false)
        .pipe(buffer())
        .pipe(uglify())
        .pipe(rev())
        .pipe(save_rev())
        .pipe(gulp.dest(conf.static));
});


function app_stream(debug) {
    var browserified = transform(function(filename) {
        var b = browserify(filename, {debug: debug});
        _.each(vendor_packages, function(v){
            b.external(v);
        });
        b.transform(reactify);
        return b.bundle();
    });

    return gulp.src([conf.js.app], {base: "."})
        .pipe(dont_break_on_errors())
        .pipe(browserified)
        .pipe(sourcemaps.init({ loadMaps: true }))
        .pipe(rename("app.js"));
}

gulp.task('scripts-app-dev', function () {
    return app_stream(true)
        .pipe(sourcemaps.write('./', {sourceRoot: fixBrowserifySourceMapPaths}))
        .pipe(gulp.dest(conf.static))
        .pipe(livereload({ auto: false }));
});

gulp.task('scripts-app-prod', function () {
    return app_stream(true)
        .pipe(buffer())
        .pipe(uglify())
        .pipe(rev())
        .pipe(sourcemaps.write('./', {sourceRoot: fixBrowserifySourceMapPaths}))
        .pipe(save_rev())
        .pipe(gulp.dest(conf.static));
});


gulp.task("jshint", function () {
    return gulp.src(conf.js.jshint)
        .pipe(dont_break_on_errors())
        .pipe(react())
        .pipe(jshint())
        .pipe(jshint.reporter("jshint-stylish"))
        .pipe(jsHintErrorReporter());
});

gulp.task("copy", function(){
    return gulp.src(conf.copy, {base: conf.src})
        .pipe(gulp.dest(conf.static));
});

function templates(){
    return gulp.src(conf.templates, {base: conf.src})
        .pipe(replace(/\{\{\{(\S*)\}\}\}/g, function(match, p1) {
            return manifest[p1];
        }))
        .pipe(gulp.dest(conf.dist));
}
gulp.task('templates', templates);

gulp.task("peg", function () {
    return gulp.src(conf.peg, {base: conf.src})
        .pipe(dont_break_on_errors())
        .pipe(peg())
        .pipe(gulp.dest("src/"));
});

gulp.task('connect', function() {
    if(conf.connect){
        connect.server({
            port: conf.connect.port
        });
    }
});

gulp.task(
    "dev",
    [
        "fonts",
        "copy",
        "styles-vendor-dev",
        "styles-app-dev",
        "scripts-vendor-dev",
        "peg",
        "scripts-app-dev",
    ],
    templates
);
gulp.task(
    "prod",
    [
        "fonts",
        "copy",
        "styles-vendor-prod",
        "styles-app-prod",
        "scripts-vendor-prod",
        "peg",
        "scripts-app-prod",
    ],
    templates
);

gulp.task("default", ["dev", "connect"], function () {
    livereload.listen({auto: true});
    gulp.watch(["src/css/vendor*"], ["styles-vendor-dev"]);
    gulp.watch(conf.peg, ["peg", "scripts-app-dev"]);
    gulp.watch(["src/js/**"], ["scripts-app-dev", "jshint"]);
    gulp.watch(["src/css/**"], ["styles-app-dev"]);
    gulp.watch(conf.templates, ["templates"]);
    gulp.watch(conf.copy, ["copy"]);
});
