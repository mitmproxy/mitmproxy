var gulp = require("gulp");
var merge = require('merge-stream');

var concat = require('gulp-concat');
var jshint = require("gulp-jshint");
var less = require("gulp-less");
var livereload = require("gulp-livereload");
var minifyCSS = require('gulp-minify-css');
var notify = require("gulp-notify");
var peg = require("gulp-peg");
var plumber = require("gulp-plumber");
var qunit = require("gulp-qunit");
var react = require("gulp-react");
var rename = require("gulp-rename");
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');


var dont_break_on_errors = function () {
    return plumber(function (error) {
        notify.onError("<%= error.message %>").apply(this, arguments);
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
        ],
        app: [
            'js/utils.js',
            'js/dispatcher.js',
            'js/actions.js',
            'js/filt/filt.js',
            'js/flow/utils.js',
            'js/store/store.js',
            'js/store/view.js',
            'js/connection.js',
            'js/components/utils.jsx.js',
            'js/components/virtualscroll.jsx.js',
            'js/components/header.jsx.js',
            'js/components/flowtable-columns.jsx.js',
            'js/components/flowtable.jsx.js',
            'js/components/flowdetail.jsx.js',
            'js/components/mainview.jsx.js',
            'js/components/eventlog.jsx.js',
            'js/components/footer.jsx.js',
            'js/components/proxyapp.jsx.js',
            'js/app.js',
        ],
    },
    peg: "js/filt/filt.pegjs",
    css: {
        vendor: ["css/vendor.less"],
        app: ["css/app.less"],
        all: ["css/**"]
    },
    vendor: ["vendor/**"],
    fonts: ["src/vendor/fontawesome/fontawesome-webfont.*"],
    html: ["*.html", "!benchmark.html", "!test.html"],
    images: ["images/**"],
    test: ["test.html"],
    opts: {base: "src", cwd: "src"}
};


gulp.task("fonts", function () {
    return gulp.src(path.fonts)
        .pipe(gulp.dest(path.dist + "static/fonts"));
});


function styles_dev(files) {
    return (gulp.src(files, path.opts)
        .pipe(dont_break_on_errors())
        .pipe(sourcemaps.init())
        .pipe(less())
        .pipe(sourcemaps.write(".", {sourceRoot: "/static"}))
        .pipe(gulp.dest(path.dist + "static"))
        .pipe(livereload({auto: false})));
}
gulp.task("styles-app-dev", styles_dev.bind(undefined, path.css.app));
gulp.task("styles-vendor-dev", styles_dev.bind(undefined, path.css.vendor));
gulp.task("styles-dev", ["styles-app-dev", "styles-vendor-dev"]);


function styles_prod(files) {
    return (gulp.src(files, path.opts)
        .pipe(less())
        // No sourcemaps support yet :-/
        // https://github.com/jonathanepollack/gulp-minify-css/issues/34
        .pipe(minifyCSS())
        .pipe(gulp.dest(path.dist + "static"))
        .pipe(livereload({auto: false})));
}
gulp.task("styles-app-prod", styles_prod.bind(undefined, path.css.app));
gulp.task("styles-vendor-prod", styles_prod.bind(undefined, path.css.vendor));
gulp.task("styles-prod", ["styles-app-prod", "styles-vendor-prod"]);


function scripts_dev(files, filename) {
    return gulp.src(files, path.opts)
        .pipe(dont_break_on_errors())
        .pipe(sourcemaps.init())
        .pipe(react())
        .pipe(concat(filename))
        .pipe(sourcemaps.write(".", {sourceRoot: "/static"}))
        .pipe(gulp.dest(path.dist + "static/js"))
        .pipe(livereload({auto: false}));
}
gulp.task("scripts-app-dev", scripts_dev.bind(undefined, path.js.app, "app.js"));
gulp.task("scripts-vendor-dev", scripts_dev.bind(undefined, path.js.vendor, "vendor.js"));
gulp.task("scripts-dev", ["scripts-app-dev", "scripts-vendor-dev"]);


function scripts_prod(files, filename) {
    return gulp.src(files, path.opts)
        .pipe(react())
        .pipe(concat(filename))
        .pipe(uglify())
        .pipe(gulp.dest(path.dist + "static/js"))
        .pipe(livereload({auto: false}));
}
gulp.task("scripts-app-prod", scripts_prod.bind(undefined, path.js.app, "app.js"));
gulp.task("scripts-vendor-prod", scripts_prod.bind(undefined, path.js.vendor, "vendor.js"));
gulp.task("scripts-prod", ["scripts-app-prod", "scripts-vendor-prod"]);


gulp.task("jshint", function () {
    return gulp.src(path.js.app.concat(["!"+path.peg.replace("pegjs","js")]), path.opts)
        .pipe(dont_break_on_errors())
        .pipe(react())
        .pipe(jshint())
        .pipe(jshint.reporter("jshint-stylish"));
});

gulp.task("peg", function () {
    return gulp.src(path.peg, path.opts)
        .pipe(dont_break_on_errors())
        .pipe(peg({exportVar:"Filt"}))
        .pipe(gulp.dest(".", path.opts));
});

gulp.task("images", function () {
    //(spriting code in commit 4ca720b55680e40b3a4361141a2ad39f9de81111)
    return gulp.src(path.images, path.opts)
        .pipe(gulp.dest(path.dist + "static"));
});

gulp.task("html", function () {
    return gulp.src(path.html, path.opts)
        .pipe(gulp.dest(path.dist + "templates"))
        .pipe(livereload({auto: false}));
});


gulp.task('test', function () {
    return gulp.src(path.test, path.opts)
        .pipe(qunit({verbose: true}));
});


common = ["fonts", "html", "jshint", "peg", "images"];
gulp.task("dev", common.concat(["styles-dev", "scripts-dev"]));
gulp.task("prod", common.concat(["styles-prod", "scripts-prod"]));

gulp.task("default", ["dev"], function () {
    livereload.listen({auto: true});
    gulp.watch(path.vendor, path.opts, ["scripts-vendor-dev", "styles-vendor-dev"]);
    gulp.watch(path.js.app, path.opts, ["scripts-app-dev", "jshint"]);
    gulp.watch(path.peg, path.opts, ["peg"]);
    gulp.watch(path.css.all, path.opts, ["styles-app-dev"]);
    gulp.watch(path.html, path.opts, ["html"]);
});
