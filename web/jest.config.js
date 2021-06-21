process.env.TZ = 'UTC';

module.exports = {
    testEnvironment: "jsdom",
    testRegex: "__tests__/.*Spec.(js|ts)x?$",
    roots: [
        "<rootDir>/src/js"
    ],
    unmockedModulePathPatterns: [
        "react"
    ],
    coverageDirectory: "./coverage",
    coveragePathIgnorePatterns: [
        "<rootDir>/src/js/filt/filt.js"
    ],
    collectCoverageFrom: [
        "src/js/**/*.{js,jsx,ts,tsx}"
    ],
    /*
    "transform": {
        "^.+\\.(t|j)sx?$": [
            "@swc-node/jest",
            {
                "parser": {
                    "jsx": true
                }
            },
        ],
    }
    /**/
    "transform": {
        "^.+\\.[jt]sx?$": [
            "esbuild-jest",
            {
                "loaders": {
                    ".js": "tsx"
                },
                "format": "cjs",
                "sourcemap": true,
            }
        ]
    }
}
