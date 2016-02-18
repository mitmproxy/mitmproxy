
var conf = {
    src: "src/",
    dist: "../mitmproxy/web",
    static: "../mitmproxy/web/static",
    js: {
        // Don't package these in the vendor distribution
        vendor_excludes: [
            "bootstrap" // We only use Bootstrap's CSS.
        ],
        // Package these as well as the dependencies
        vendor_includes: [
            "react/addons"
        ],
        app: 'src/js/app.js',
        eslint: ["src/js/**/*.js", "!src/js/filt/filt.js"]
    },
    css: {
        vendor: ["src/css/vendor.less"],
        app: ["src/css/app.less"]
    },
    copy: [
        "src/images/**", "src/fonts/fontawesome-webfont.*"
    ],
    templates: [
        "src/templates/*"
    ],
    peg: ["src/js/filt/filt.peg"]
};

module.exports = conf;