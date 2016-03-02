var path = require('path');

var packagejs = require('./package.json');
var conf = require('./conf.js');

// Sorted alphabetically!
var babelify = require('babelify');
var browserify = require('browserify');
var gulp = require("gulp");
var eslint = require('gulp-eslint');
var less = require("gulp-less");
var livereload = require("gulp-livereload");
var minifyCSS = require('gulp-minify-css');
var notify = require("gulp-notify");
var peg = require("gulp-peg");
var plumber = require("gulp-plumber");
var rename = require("gulp-rename");
var sourcemaps = require('gulp-sourcemaps');
var gutil = require("gulp-util");
var _ = require('lodash');
var uglifyify = require('uglifyify');
var buffer = require('vinyl-buffer');
var source = require('vinyl-source-stream');
var watchify = require('watchify');

var vendor_packages = _.difference(
    _.union(
        _.keys(packagejs.dependencies),
        conf.js.vendor_includes
    ),
    conf.js.vendor_excludes
);

var handleError = {errorHandler: notify.onError("Error: <%= error.message %>")};

/*
 * Sourcemaps are a wonderful way to develop directly from the chrome devtools.
 * However, generating correct sourcemaps is a huge PITA, especially on Windows.
 * Fixing this upstream is tedious as apparently nobody really cares and
 * a single misbehaving transform breaks everything.
 * Thus, we just manually fix all paths.
 */
function fixSourceMaps(file) {
    file.sourceMap.sources = file.sourceMap.sources.map(function (x) {
        return path.relative(".", x).split(path.sep).join('/');
    });
    return "/";
}
// Browserify fails for paths starting with "..".
function fixBrowserifySourceMaps(file) {
    file.sourceMap.sources = file.sourceMap.sources.map((x) => {
        return x.replace("src/js/node_modules", "node_modules");
    });
    return fixSourceMaps(file);
}
function fixLessSourceMaps(file) {
    file.sourceMap.sources = file.sourceMap.sources.map((x) => {
        if(!x.startsWith("..")){
            return "../src/css/" + x;
        }
        return x.replace("src/js/node_modules", "node_modules");
    });
    return fixSourceMaps(file);
}

function styles(files, dev){
    return gulp.src(files)
        .pipe(dev ? plumber(handleError) : gutil.noop())
        .pipe(sourcemaps.init())
        .pipe(less())
        .pipe(dev ? gutil.noop() : minifyCSS())
        .pipe(sourcemaps.write(".", {sourceRoot: fixLessSourceMaps}))
        .pipe(gulp.dest(conf.static))
        .pipe(livereload({auto: false}));
}
gulp.task("styles-app-dev", function () {
    styles(conf.css.app, true);
});
gulp.task("styles-vendor-dev", function () {
    styles(conf.css.vendor, true);
});
gulp.task("styles-app-prod", function () {
    styles(conf.css.app, false);
});
gulp.task("styles-vendor-prod", function () {
    styles(conf.css.app, false);
});


function buildScript(bundler, filename, dev) {
    if (dev) {
        bundler = watchify(bundler);
    } else {
        bundler = bundler.transform({global: true}, uglifyify);
    }

    function rebundle() {
        return bundler.bundle()
            .on('error', function(error) {
                gutil.log(error + '\n' + error.codeFrame);
                this.emit('end');
            })
            .pipe(dev ? plumber(handleError) : gutil.noop())
            .pipe(source('bundle.js'))
            .pipe(buffer())
            .pipe(sourcemaps.init({loadMaps: true}))
            .pipe(rename(filename))
            .pipe(sourcemaps.write('.', {sourceRoot: fixBrowserifySourceMaps}))
            .pipe(gulp.dest(conf.static))
            .pipe(livereload({auto: false}));
    }

    // listen for an update and run rebundle
    bundler.on('update', rebundle);
    bundler.on('log', gutil.log);
    bundler.on('error', gutil.log);

    // run it once the first time buildScript is called
    return rebundle();
}

function vendor_stream(dev) {
    var bundler = browserify({
        entries: [],
        debug: true,
        cache: {}, // required for watchify
        packageCache: {} // required for watchify
    });
    for (var vp of vendor_packages) {
        bundler.require(vp);
    }
    return buildScript(bundler, "vendor.js", dev);
}
gulp.task("scripts-vendor-dev", function () {
    return vendor_stream(true);
});
gulp.task("scripts-vendor-prod", function () {
    return vendor_stream(false);
});

function app_stream(dev) {
    var bundler = browserify({
        entries: [conf.js.app],
        debug: true,
        cache: {}, // required for watchify
        packageCache: {} // required for watchify
    });
    for (var vp of vendor_packages) {
        bundler.external(vp);
    }
    bundler = bundler.transform(babelify);
    return buildScript(bundler, "app.js", dev);
}
gulp.task('scripts-app-dev', function () {
    return app_stream(true);
});
gulp.task('scripts-app-prod', function () {
    return app_stream(false);
});


gulp.task("eslint", function () {
    return gulp.src(conf.js.eslint)
        .pipe(plumber(handleError))
        .pipe(eslint())
        .pipe(eslint.format())
});

gulp.task("copy", function () {
    return gulp.src(conf.copy, {base: conf.src})
        .pipe(gulp.dest(conf.static));
});


gulp.task('templates', function(){
    return gulp.src(conf.templates, {base: conf.src})
        .pipe(gulp.dest(conf.dist));
});

gulp.task("peg", function () {
    return gulp.src(conf.peg, {base: conf.src})
        .pipe(plumber(handleError))
        .pipe(peg())
        .pipe(gulp.dest("src/"));
});

gulp.task(
    "dev",
    [
        "copy",
        "styles-vendor-dev",
        "styles-app-dev",
        "scripts-vendor-dev",
        "peg",
        "scripts-app-dev",
        "templates"
    ]
);
gulp.task(
    "prod",
    [
        "copy",
        "styles-vendor-prod",
        "styles-app-prod",
        "scripts-vendor-prod",
        "peg",
        "scripts-app-prod",
        "templates"
    ]
);

gulp.task("default", ["dev"], function () {
    livereload.listen({auto: true});
    gulp.watch(["src/css/vendor*"], ["styles-vendor-dev"]);
    gulp.watch(["src/css/**"], ["styles-app-dev"]);

    gulp.watch(conf.templates, ["templates"]);
    gulp.watch(conf.peg, ["peg"]);
    gulp.watch(["src/js/**"], ["eslint"]);
    // other JS is handled by watchify.
    gulp.watch(conf.copy, ["copy"]);
});
