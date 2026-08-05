import * as React from "react";
import { render, screen } from "../test-utils";
import Footer from "../../components/Footer";
import { TStore } from "../ducks/tutils";

test("renders active options as badges", () => {
    const state = TStore().getState();
    const store = TStore({
        ...state,
        options: {
            ...state.options,
            mode: ["regular", "upstream:https://example.com"],
            intercept: "~q",
            ssl_insecure: true,
            showhost: true,
            upstream_cert: false,
            rawtcp: false,
            http2: false,
            websocket: false,
            anticache: true,
            anticomp: true,
            stickyauth: "~u example.com",
            stickycookie: "~d example.com",
            stream_large_bodies: "1048576",
            listen_host: "127.0.0.1",
            listen_port: 9090,
            server: true,
        },
    });

    render(<Footer />, { store });

    [
        "regular,upstream:https://example.com",
        "Intercept: ~q",
        "ssl_insecure",
        "showhost",
        "no-upstream-cert",
        "no-raw-tcp",
        "no-http2",
        "no-websocket",
        "anticache",
        "anticomp",
        "stickyauth: ~u example.com",
        "stickycookie: ~d example.com",
        "stream: 1mb",
        "1 of 5 flows selected",
        "127.0.0.1:9090",
        "mitmproxy 1.2.3",
    ].forEach((text) => expect(screen.getByText(text)).toBeVisible());
});
