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
            'js/dispatcher.js',
            'js/actions.js',
            'js/stores/base.js',
            'js/stores/settingstore.js',
            'js/stores/eventlogstore.js',
            'js/connection.js',
            'js/components/header.jsx',
            'js/components/traffictable.jsx',
            'js/components/eventlog.jsx',
            'js/components/footer.jsx',
            'js/components/proxyapp.jsx',
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


function styles_dev(files) {
    return (gulp.src(files, {base: "src", cwd: "src"})
        .pipe(dont_break_on_errors())
        .pipe(sourcemaps.init())
        .pipe(less())
        .pipe(sourcemaps.write(".", {sourceRoot: "/static"}))
        .pipe(gulp.dest(path.dist + "static"))
        .pipe(livereload({ auto: false })));
}
gulp.task("styles-app-dev", styles_dev.bind(undefined, path.css.app));
gulp.task("styles-vendor-dev", styles_dev.bind(undefined, path.css.vendor));
gulp.task("styles-dev", ["styles-app-dev", "styles-vendor-dev"]);


function styles_prod(files) {
    return (gulp.src(files, {base: "src", cwd: "src"})
        .pipe(less())
        // No sourcemaps support yet :-/
        // https://github.com/jonathanepollack/gulp-minify-css/issues/34
        .pipe(minifyCSS())
        .pipe(gulp.dest(path.dist + "static"))
        .pipe(livereload({ auto: false })));
}
gulp.task("styles-app-prod", styles_prod.bind(undefined, path.css.app));
gulp.task("styles-vendor-prod", styles_prod.bind(undefined, path.css.vendor));
gulp.task("styles-prod", ["styles-app-prod", "styles-vendor-prod"]);


function scripts_dev(files, filename) {
    return gulp.src(files, {base: "src", cwd: "src"})
        .pipe(dont_break_on_errors())
        .pipe(sourcemaps.init())
        .pipe(react())
        .pipe(concat(filename))
        .pipe(sourcemaps.write(".", {sourceRoot: "/static"}))
        .pipe(gulp.dest(path.dist + "static/js"))
        .pipe(livereload({ auto: false }));
}
gulp.task("scripts-app-dev", scripts_dev.bind(undefined, path.js.app, "app.js"));
gulp.task("scripts-vendor-dev", scripts_dev.bind(undefined, path.js.vendor, "vendor.js"));
gulp.task("scripts-dev", ["scripts-app-dev", "scripts-vendor-dev"]);


function scripts_prod(files, filename) {
    return gulp.src(files, {base: "src", cwd: "src"})
        .pipe(react())
        .pipe(concat(filename))
        .pipe(uglify())
        .pipe(gulp.dest(path.dist + "static/js"))
        .pipe(livereload({ auto: false }));
}
gulp.task("scripts-app-prod", scripts_prod.bind(undefined, path.js.app, "app.js"));
gulp.task("scripts-vendor-prod", scripts_prod.bind(undefined, path.js.vendor, "vendor.js"));
gulp.task("scripts-prod", ["scripts-app-prod", "scripts-vendor-prod"]);


gulp.task("jshint", function () {
    return gulp.src(["src/js/**"])
        .pipe(dont_break_on_errors())
        .pipe(react())
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
