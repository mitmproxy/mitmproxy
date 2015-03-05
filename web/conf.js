
var conf = {
    src: "src/",
    dist: "../libmproxy/web",
    static: "../libmproxy/web/static",
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
        jshint: ["src/js/**.js", "!src/js/filt/filt.js"]
    },
    css: {
        vendor: ["src/css/vendor.less"],
        app: ["src/css/app.less"]
    },
    copy: [
        "src/images/**",
    ],
    templates: [
        "src/templates/*"
    ],
    fonts: ["src/fontawesome/fontawesome-webfont.*"],
    peg: ["src/js/filt/filt.peg"],
    connect: false
};

module.exports = conf;