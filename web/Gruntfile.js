var cssfiles = {
    "../libmproxy/web/static/css/app.css": "src/css/app.less",
    "../libmproxy/web/static/css/vendor.css": "src/css/vendor.less",
};
var jsfiles = {
    "../libmproxy/web/static/js/vendor.js": [
        'src/vendor/jquery/jquery.js',
        'src/vendor/lodash/lodash.js',
        'src/vendor/react/react-with-addons.js',
        'src/vendor/react-router/react-router.js',
        'src/vendor/react-bootstrap/react-bootstrap.js',
    ],
    "../libmproxy/web/static/js/app.js": [
        'src/js/datastructures.compiled.js',
        'src/js/footer.compiled.js',
        'src/js/header.compiled.js',
        'src/js/mitmproxy.compiled.js',
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
                        src: ['src/vendor/fontawesome/fontawesome-webfont.*'],
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
                    src: ['*.react.js','*.es6.js'],
                    dest: 'src/js',
                    ext: '.compiled.js'
                }]
            },
            options: {
                harmony: true
            }
        },
        uglify: {
            dev: {
                options: {
                    mangle: false,
                    compress: false,
                    beautify: true,
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
                jshintrc: ".jshintrc",
            },
            all: ['src/js/*.js','!src/js/*.react.js'],
            gruntfile: ['Gruntfile.js']
        },
        qunit: {
            all: ['src/test.html']
        },
        watch: {
            less: {
                files: ['src/css/**'],
                tasks: ['less:dev'],
                options: {
                    livereload: true,
                }
            },
            jsx: {
                files: ['src/js/*.react.js','src/js/*.es6.js'],
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