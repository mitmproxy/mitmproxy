/* eslint-disable @typescript-eslint/no-require-imports */
const gulp = require("gulp");
const gulpEsbuild = require("gulp-esbuild");
const less = require("gulp-less");
const livereload = require("gulp-livereload");
const cleanCSS = require("gulp-clean-css");
const notify = require("gulp-notify");
const compilePeg = require("gulp-peg");
const plumber = require("gulp-plumber");
const replace = require("gulp-replace");
const sourcemaps = require("gulp-sourcemaps");
const through = require("through2");

const noop = () => through.obj();

var handleError = {
    errorHandler: notify.onError("Error: <%= error.message %>"),
};

function styles(files, dev) {
    return gulp
        .src(files)
        .pipe(dev ? plumber(handleError) : noop())
        .pipe(sourcemaps.init())
        .pipe(less())
        .pipe(dev ? noop() : cleanCSS())
        .pipe(sourcemaps.write(".", { sourceRoot: "/src/css" }))
        .pipe(gulp.dest("../mitmproxy/tools/web/static"))
        .pipe(livereload({ auto: false }));
}

function styles_vendor_prod() {
    return styles("src/css/vendor.less", false);
}

function styles_vendor_dev() {
    return styles("src/css/vendor.less", true);
}

function styles_app_prod() {
    return styles("src/css/app.less", false);
}

function styles_app_dev() {
    return styles("src/css/app.less", true);
}

function esbuild(dev) {
    return gulp
        .src("src/js/app.tsx")
        .pipe(
            gulpEsbuild({
                outfile: "app.js",
                sourcemap: true,
                sourceRoot: "/",
                minify: !dev,
                keepNames: true,
                bundle: true,
            }),
        )
        .pipe(gulp.dest("../mitmproxy/tools/web/static"))
        .pipe(livereload({ auto: false }));
}

function scripts_dev() {
    return esbuild(true);
}

function scripts_prod() {
    return esbuild(false);
}

const copy_src = [
    "src/images/**",
    "src/fonts/fontawesome-webfont.*",
    "!**/*.psd",
];

function copy() {
    return gulp
        .src(copy_src, { base: "src/", encoding: false })
        .pipe(gulp.dest("../mitmproxy/tools/web/static"));
}

const peg_src = "src/js/filt/*.peg";

function peg() {
    return gulp
        .src(peg_src, { base: "src/" })
        .pipe(plumber(handleError))
        .pipe(compilePeg())
        .pipe(
            replace(
                "module.exports = ",
                "/* eslint-disable */\n" +
                    'import * as flowutils from "../flow/utils"\n' +
                    "export default ",
            ),
        )
        .pipe(gulp.dest("src/"));
}

const dev = gulp.parallel(
    copy,
    styles_vendor_dev,
    styles_app_dev,
    peg,
    scripts_dev,
);

const prod = gulp.parallel(
    copy,
    styles_vendor_prod,
    styles_app_prod,
    peg,
    scripts_prod,
);

exports.dev = dev;
exports.prod = prod;
exports.default = function watch() {
    const opts = { ignoreInitial: false };
    livereload.listen({ auto: true });
    gulp.watch(["src/css/vendor*"], opts, styles_vendor_dev);
    gulp.watch(["src/css/**"], opts, styles_app_dev);
    gulp.watch(["src/js/**"], opts, scripts_dev);
    gulp.watch(peg_src, opts, peg);
    gulp.watch(copy_src, opts, copy);
};
