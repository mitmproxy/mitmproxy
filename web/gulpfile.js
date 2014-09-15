var gulp = require("gulp");

var concat = require('gulp-concat');
var gutil = require('gulp-util');
var jshint = require("gulp-jshint");
var less = require("gulp-less");
var livereload = require("gulp-livereload");
var minifyCSS = require('gulp-minify-css');
var notify = require("gulp-notify");
var plumber = require("gulp-plumber");
var qunit = require("gulp-qunit");
var react = require("gulp-react");
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');


var dont_break_on_errors = function(){
    return plumber(function(error){
        notify.onError("Error: <%= error.message %>").apply(this, arguments);
        this.emit('end');
    });
};

var path = {
    dist: "../libmproxy/web/",
    js: {
        vendor: [
            'vendor/jquery/jquery.js',
            'vendor/lodash/lodash.js',
            'vendor/react/react-with-addons.js',
            'vendor/react-router/react-router.js',
            'vendor/react-bootstrap/react-bootstrap.js'
        ],
        app: [
            'js/Dispatcher.es6.js',
            'js/actions.es6.js',
            'js/stores/base.es6.js',
            'js/stores/SettingsStore.es6.js',
            'js/stores/EventLogStore.es6.js',
            'js/Connection.es6.js',
            'js/components/Header.react.js',
            'js/components/TrafficTable.react.js',
            'js/components/EventLog.react.js',
            'js/components/Footer.react.js',
            'js/components/ProxyApp.react.js',
            'js/app.js',
        ],
    },
    css: {
        vendor: ["css/vendor.less"],
        app: ["css/app.less"]
    },
    fonts: ["src/vendor/fontawesome/fontawesome-webfont.*"],
    html: ["src/*.html", "!src/benchmark.html", "!src/test.html"]
};
gulp.task("fonts", function () {
    return gulp.src(path.fonts)
        .pipe(gulp.dest(path.dist + "static/fonts"));
});

function styles(files, dev) {
    return (gulp.src(files, {base: "src", cwd: "src"})
        .pipe(dev ? dont_break_on_errors() : gutil.noop())
        .pipe(dev ? sourcemaps.init() : gutil.noop())
        .pipe(less())
        .pipe(dev ? sourcemaps.write(".", {sourceRoot: "/static"}) : gutil.noop())
        // No sourcemaps support yet :-/
        // https://github.com/jonathanepollack/gulp-minify-css/issues/34
        .pipe(!dev ? minifyCSS() : gutil.noop())
        .pipe(gulp.dest(path.dist + "static"))
        .pipe(livereload({ auto: false })));
}
gulp.task("styles-app-dev", styles.bind(undefined, path.css.app, true));
gulp.task("styles-app-prod", styles.bind(undefined, path.css.app, false));
gulp.task("styles-vendor-dev", styles.bind(undefined, path.css.vendor, true));
gulp.task("styles-vendor-prod", styles.bind(undefined, path.css.vendor, false));
gulp.task("styles-dev", ["styles-app-dev", "styles-vendor-dev"]);
gulp.task("styles-prod", ["styles-app-prod", "styles-vendor-prod"]);

function scripts(files, filename, dev) {
    return gulp.src(files, {base: "src", cwd: "src"})
        .pipe(dev ? dont_break_on_errors(): gutil.noop())
        .pipe(dev ? sourcemaps.init() : gutil.noop())
        .pipe(react({harmony: true}))
        .pipe(concat(filename))
        .pipe(!dev ? uglify() : gutil.noop())
        .pipe(dev ? sourcemaps.write(".", {sourceRoot: "/static"}) : gutil.noop())
        .pipe(gulp.dest(path.dist + "static/js"))
        .pipe(livereload({ auto: false }));
}
gulp.task("scripts-app-dev", scripts.bind(undefined, path.js.app, "app.js", true));
gulp.task("scripts-app-prod", scripts.bind(undefined, path.js.app, "app.js", false));
gulp.task("scripts-vendor-dev", scripts.bind(undefined, path.js.vendor, "vendor.js", true));
gulp.task("scripts-vendor-prod", scripts.bind(undefined, path.js.vendor, "vendor.js", false));
gulp.task("scripts-dev", ["scripts-app-dev", "scripts-vendor-dev"]);
gulp.task("scripts-prod", ["scripts-app-prod", "scripts-vendor-prod"]);

gulp.task("jshint", function () {
    return gulp.src(["src/js/**"])
        .pipe(dont_break_on_errors())
        .pipe(react({harmony: false /* Do not do Harmony transformation for JSHint */}))
        .pipe(jshint())
        .pipe(jshint.reporter("jshint-stylish"))
});

gulp.task("html", function () {
    return gulp.src(path.html)
        .pipe(gulp.dest(path.dist + "templates"))
        .pipe(livereload({ auto: false }));
});

gulp.task('test', function() {
    return gulp.src('src/test.html')
        .pipe(qunit({verbose: true}));
});

common = ["fonts", "html", "jshint"];
gulp.task("dev", common.concat(["styles-dev", "scripts-dev"]));
gulp.task("prod", common.concat(["styles-prod", "scripts-prod"]));

gulp.task("default", ["dev"], function () {
    livereload.listen({auto: true});
    gulp.watch(["src/vendor/**"], ["scripts-vendor-dev", "styles-vendor-dev"]);
    gulp.watch(["src/js/**"], ["scripts-app-dev", "jshint"]);
    gulp.watch(["src/css/**"], ["styles-app-dev"]);
    gulp.watch(["src/*.html"], ["html"]);
});
