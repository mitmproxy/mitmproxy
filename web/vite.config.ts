import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
    plugins: [
        react({
            babel: {
                plugins: [["babel-plugin-react-compiler", {}]],
            },
        }),
    ],
    base: "",
    build: {
        outDir: "../mitmproxy/tools/web",
        assetsDir: "static",
    },
    server: {
        host: "127.0.0.1",
        proxy: {
            "^/(?!@|src|node_modules|updates).+": {
                target: "http://127.0.0.1:8081",
            },
            "/updates": {
                target: "ws://127.0.0.1:8081",
                ws: true,
            },
        },
    },
});
