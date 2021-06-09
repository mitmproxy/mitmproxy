process.env.TZ = 'UTC';

module.exports = {
    "testRegex": "__tests__/.*Spec.js$",
    "roots": [
        "<rootDir>/src/js"
    ],
    "unmockedModulePathPatterns": [
        "react"
    ],
    "coverageDirectory": "./coverage",
    "coveragePathIgnorePatterns": [
        "<rootDir>/src/js/filt/filt.js"
    ],
    "collectCoverageFrom": [
        "src/js/**/*.{js,jsx}"
    ]
};
