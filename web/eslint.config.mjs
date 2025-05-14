import globals from "globals";
import pluginJs from "@eslint/js";
import tseslint from "typescript-eslint";
import pluginReactConfig from "eslint-plugin-react/configs/recommended.js";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
    { files: ["**/*.{ts,tsx}"] },
    { languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } } },
    { languageOptions: { globals: globals.browser } },
    pluginJs.configs.recommended,
    ...tseslint.configs.recommended,
    pluginReactConfig,
    {
        rules: {
            "@typescript-eslint/no-empty-object-type": "off",
            "@typescript-eslint/no-explicit-any": "off",
            "@typescript-eslint/no-unused-vars": [
                "error",
                {
                    args: "after-used",
                    argsIgnorePattern: "^_",
                    varsIgnorePattern: "^_",
                },
            ],
            "one-var": ["error", { const: "never", let: "consecutive" }],
        },
        settings: {
            react: {
                version: "detect",
            },
        },
    },
    {
        files: ["src/**/*Spec.{ts,tsx}"],
        rules: {
            "prefer-const": "off",
        },
    },
    {
        files: ["jest.config.js", "gulpfile.js", "setup-jest.js"],
        languageOptions: { globals: globals.node },
    },
    {
        files: ["src/**/*.{js,jsx}"],
        rules: {
            "no-restricted-syntax": [
                "error",
                {
                    selector: "*",
                    message: "Only TypeScript (ts, tsx) files are allowed.",
                },
            ],
        },
    },
    globalIgnores(["coverage/*"]),
]);
