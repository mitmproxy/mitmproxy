var gulp = require("gulp");
var path = require('path');
var _ = require('lodash');

var browserify = require('browserify');
var concat = require('gulp-concat');
var connect = require('gulp-connect');
var buffer = require('vinyl-buffer');
var jshint = require("gulp-jshint");
var less = require("gulp-less");
var livereload = require("gulp-livereload");
var map = require("map-stream");
var minifyCSS = require('gulp-minify-css');
var notify = require("gulp-notify");
var plumber = require("gulp-plumber");
var rev = require("gulp-rev");
var react = require("gulp-react");
var reactify = require('reactify');
var rename = require("gulp-rename");
var replace = require('gulp-replace');
var source = require('vinyl-source-stream');
var sourcemaps = require('gulp-sourcemaps');
var transform = require('vinyl-transform');
var uglify = require('gulp-uglify');

var packagejs = require('./package.json');


// FIXME: react-with-addons.min.js for prod use issue

var manifest = {
    "vendor.css": "vendor.css",
    "app.css": "app.css",
    "vendor.js": "vendor.js",
    "app.js": "app.js",
};

var CONF = {
    dist: "../libmproxy/web",
    static: "../libmproxy/web/static",
    js: {
        // Don't package these in the vendor distribution
        vendor_excludes: [
            "bootstrap"
        ],
        // Package these as well as the dependencies
        vendor_includes: [
            "react/addons"
        ],
        app: 'src/js/app.js'
    },
    css: {
        vendor: ["src/css/vendor.less"],
        app: ["src/css/app.less"]
    },
    copy: [
        "src/examples/**",
        "src/fonts/**",
    ],
    templates: [
        "src/templates/*"
    ],
    fonts: ["src/fontawesome/fontawesome-webfont.*"],
    port: 8082
};

var vendor_packages = _.difference(
        _.union(
            _.keys(packagejs.dependencies),
            CONF.js.vendor_includes
        ),
        CONF.js.vendor_excludes
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

var save_rev = function(){
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


gulp.task("fonts", function () {
    return gulp.src(CONF.fonts)
        .pipe(gulp.dest(CONF.dist + "fonts"));
});


function styles_dev(files) {
    return (gulp.src(files)
        .pipe(dont_break_on_errors())
        .pipe(sourcemaps.init())
        .pipe(less())
        .pipe(sourcemaps.write(".", {sourceRoot: "/static"}))
        .pipe(gulp.dest(CONF.static))
        .pipe(livereload({ auto: false })));
}
gulp.task("styles-app-dev", function(){
    styles_dev(CONF.css.app);
}); 
gulp.task("styles-vendor-dev", function(){
    styles_dev(CONF.css.vendor);
}); 


function styles_prod(files) {
    return (gulp.src(files)
        .pipe(less())
        // No sourcemaps support yet :-/
        // https://github.com/jonathanepollack/gulp-minify-css/issues/34
        .pipe(minifyCSS())
        .pipe(rev())
        .pipe(save_rev())
        .pipe(gulp.dest(CONF.static))
        .pipe(livereload({ auto: false })));
}
gulp.task("styles-app-prod", function(){
    styles_prod(CONF.css.app);
}); 
gulp.task("styles-vendor-prod", function(){
    styles_prod(CONF.css.vendor);
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
    return vendor_stream(true)
        .pipe(gulp.dest(CONF.static));
});
gulp.task("scripts-vendor-prod", function(){
    return vendor_stream(false)
        .pipe(buffer())
        .pipe(uglify())
        .pipe(rev())
        .pipe(save_rev())
        .pipe(gulp.dest(CONF.static));
});


function app_stream(debug) {
    var browserified = transform(function(filename) {
        var b = browserify(filename, {debug: debug})
        _.each(vendor_packages, function(v){
            b.external(v);
        });
        b.transform(reactify);
        return b.bundle();
    });
    return gulp.src([CONF.js.app])
        .pipe(dont_break_on_errors())
        .pipe(browserified)
        .pipe(rename("app.js"));
};
gulp.task('scripts-app-dev', function () {
    return app_stream(true)
        .pipe(gulp.dest(CONF.static))
        .pipe(livereload({ auto: false }));
});
gulp.task('scripts-app-prod', function () {
    return app_stream(true)
        .pipe(buffer())
        .pipe(uglify())
        .pipe(rev())
        .pipe(save_rev())
        .pipe(gulp.dest(CONF.static));
});


gulp.task("jshint", function () {
    return gulp.src(["src/js/**.js"])
        .pipe(dont_break_on_errors())
        .pipe(react())
        .pipe(plumber())
        .pipe(jshint())
        .pipe(jshint.reporter("jshint-stylish"))
        .pipe(jsHintErrorReporter());
});

gulp.task("copy", function(){
    return gulp.src(CONF.copy, {base:"src/"})
        .pipe(gulp.dest(CONF.dist));
});

function templates(){
    return gulp.src(CONF.templates, {base:"src/"})
        .pipe(replace(/\{\{\{(\S*)\}\}\}/g, function(match, p1) {
            return manifest[p1];
        })) 
        .pipe(gulp.dest(CONF.dist));
};
gulp.task('templates', templates);


gulp.task('connect', function() {
    connect.server({
        port: CONF.port
    });
});

common = ["fonts", "copy"];
gulp.task(
    "dev",
    [
        "fonts",
        "copy",
        "styles-vendor-dev",
        "styles-app-dev",
        "scripts-vendor-dev",
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
        "scripts-app-prod",
        "connect"
    ],
    templates
);

gulp.task("default", ["dev", "connect"], function () {
    livereload.listen({auto: true});
    gulp.watch(["src/css/vendor*"], ["styles-vendor-dev"]);
    gulp.watch(["src/js/**"], ["scripts-app-dev", "jshint"]);
    gulp.watch(["src/css/**"], ["styles-app-dev"]);
    gulp.watch(CONF.templates, ["templates"]);
    gulp.watch(CONF.copy, ["copy"]);
});
