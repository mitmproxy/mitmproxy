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
var peg = require("gulp-peg");
var filelog = require('gulp-filelog');

var packagejs = require('./package.json');
var conf = require('./conf.js');


// FIXME: react-with-addons.min.js for prod use issue

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
    return gulp.src(conf.fonts)
        .pipe(gulp.dest(conf.dist + "fonts"));
});


function styles_dev(files) {
    return (gulp.src(files)
        .pipe(dont_break_on_errors())
        .pipe(sourcemaps.init())
        .pipe(less())
        .pipe(sourcemaps.write(".", {sourceRoot: "/static"}))
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
        // No sourcemaps support yet :-/
        // https://github.com/jonathanepollack/gulp-minify-css/issues/34
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
    return vendor_stream(true)
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
        var b = browserify(filename, {debug: debug})
        _.each(vendor_packages, function(v){
            b.external(v);
        });
        b.transform(reactify);
        return b.bundle();
    });
    return gulp.src([conf.js.app])
        .pipe(dont_break_on_errors())
        .pipe(browserified)
        .pipe(rename("app.js"));
};
gulp.task('scripts-app-dev', function () {
    return app_stream(true)
        .pipe(gulp.dest(conf.static))
        .pipe(livereload({ auto: false }));
});
gulp.task('scripts-app-prod', function () {
    return app_stream(true)
        .pipe(buffer())
        .pipe(uglify())
        .pipe(rev())
        .pipe(save_rev())
        .pipe(gulp.dest(conf.static));
});


gulp.task("jshint", function () {
    return gulp.src(conf.js.jshint)
        .pipe(dont_break_on_errors())
        .pipe(react())
        .pipe(plumber())
        .pipe(jshint())
        .pipe(jshint.reporter("jshint-stylish"))
        .pipe(jsHintErrorReporter());
});

gulp.task("copy", function(){
    return gulp.src(conf.copy, {base:"src/"})
        .pipe(gulp.dest(conf.dist));
});

function templates(){
    return gulp.src(conf.templates, {base:"src/"})
        .pipe(replace(/\{\{\{(\S*)\}\}\}/g, function(match, p1) {
            return manifest[p1];
        })) 
        .pipe(gulp.dest(conf.dist));
};
gulp.task('templates', templates);

gulp.task("peg", function () {
    return gulp.src(conf.peg, {base: "src/"})
        .pipe(dont_break_on_errors())
        .pipe(peg())
        .pipe(filelog())
        .pipe(gulp.dest("src/"));
});

gulp.task('connect', function() {
    connect.server({
        port: conf.port
    });
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
        "connect"
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
