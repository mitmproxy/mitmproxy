var cssfiles = {
    "../libmproxy/web/static/mitmproxy.css": "src/css/mitmproxy.less",
};
var jsfiles = {
    "../libmproxy/web/static/mitmproxy.js": [
        'src/vendor/jquery/jquery.js',
        'src/vendor/lodash/dist/lodash.js',
        'src/vendor/react/react-with-addons.js',
        'src/vendor/react-router/dist/react-router.js',
        'src/vendor/bootstrap-customized.js',
        'src/js/router_jsx.js',
        'src/js/certinstall_jsx.js',
        'src/js/mitmproxy.js',
    ],
};

module.exports = function (grunt) {
    "use strict";
    grunt.initConfig({
        pkg: grunt.file.readJSON("package.json"),
        copy: {
            all: {
                files: [
                    {
                        expand: true,
                        flatten: true,
                        src: ['src/vendor/fontawesome/fonts/*'],
                        dest: '../libmproxy/web/static/fonts'
                    }
                ],
            }
        },
        less: {
            dev: {
                options: {
                    paths: ["src/css"],
                    sourceMap: true
                },
                files: cssfiles
            },
            prod: {
                options: {
                    paths: ["src/css"],
                    cleancss: true,
                    report: "gzip"
                },
                files: cssfiles
            }
        },
        react: {
            all: {
                files: [{
                    expand: true,
                    cwd: 'src/js',
                    src: ['*.jsx'],
                    dest: 'src/js',
                    ext: '_jsx.js'
                }]
            }
        },
        uglify: {
            dev: {
                options: {
                    mangle: false,
                    compress: false,
                    sourceMap: true,
                    sourceMapIncludeSources: true,
                },
                files: jsfiles
            },
            prod: {
                options: {
                    report: "gzip",
                    compress: true,
                },
                files: jsfiles
            },
        },
        jshint: {
            options: {
              loopfunc: true,
            },
            all: ['src/js/*.js'],
            gruntfile: ['Gruntfile.js']
        },
        qunit: {
            all: ['src/test.html']
        },
        watch: {
            less: {
                files: ['src/css/*.less', 'src/css/*.css'],
                tasks: ['less:dev'],
                options: {
                    livereload: true,
                }
            },
            jsx: {
                files: ['src/js/*.jsx'],
                tasks: ['react:all'],
            },
            js: {
                files: ['src/js/*.js'],
                tasks: ['jshint:all', 'uglify:dev'],
                options: {
                    livereload: true,
                }
            },
            copy: {
                files: ['src/*.html', 'src/examples/**'],
                tasks: ['copy:all'],
                options: {
                    livereload: true,
                }
            },
            gruntfile: {
                files: './Gruntfile.js',
                tasks: ['jshint:gruntfile'],
            },
        },
        notify: {
            done: {
                options: {
                    message: 'Done!'
                }
            }
        }
    });

    grunt.loadNpmTasks('grunt-contrib-less');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-jshint');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-contrib-qunit');
    grunt.loadNpmTasks('grunt-notify');
    grunt.loadNpmTasks('grunt-shell');
    grunt.loadNpmTasks('grunt-react');
    grunt.registerTask(
        'prod', ['react:all', 'jshint:all', 'copy:all', 'uglify:prod', 'less:prod']
    );
    grunt.registerTask(
        'dev', ['react:all', 'jshint:all', 'copy:all', 'uglify:dev', 'less:dev']
    );
    grunt.registerTask('test', ['qunit:all']);

};