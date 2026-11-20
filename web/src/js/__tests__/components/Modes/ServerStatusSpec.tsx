import * as React from "react";
import QRCode from "qrcode";
import { render } from "../../test-utils";
import { ServerStatus } from "../../../components/Modes/CaptureSetup";

jest.mock("qrcode", () => ({ toCanvas: jest.fn() }));

test("WireGuard QR code has a quiet zone", () => {
    render(
        <ServerStatus
            backendState={{
                description: "WireGuard server",
                full_spec: "wireguard",
                is_running: true,
                last_exception: null,
                listen_addrs: [["0.0.0.0", 51820]],
                type: "wireguard",
                wireguard_conf: "[Interface]\nPrivateKey = foo",
            }}
        />,
    );

    expect(QRCode.toCanvas).toHaveBeenCalledWith(
        expect.any(HTMLCanvasElement),
        "[Interface]\nPrivateKey = foo",
        expect.objectContaining({ margin: 4 }),
    );
});
