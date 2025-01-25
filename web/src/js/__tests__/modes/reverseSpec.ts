import { ReverseProxyProtocols } from "../../backends/consts";
import { ModesState } from "../../ducks/modes";
import { parseSpec } from "../../modes";
import { getSpec, parseRaw, ReverseState } from "../../modes/reverse";

describe("getSpec reverse mode", () => {
    it("should return the correct mode config", () => {
        const modes = {
            reverse: [
                {
                    active: true,
                    protocol: ReverseProxyProtocols.HTTPS,
                    destination: "example.com:8085",
                    listen_host: "localhost",
                    listen_port: 8082,
                },
            ],
        } as ModesState;
        const mode = getSpec(modes.reverse[0]);
        expect(mode).toBe("reverse:https://example.com:8085@localhost:8082");
    });
});

describe("parseRaw reverse mode", () => {
    it("should parse", () => {
        const parsed = parseRaw(
            parseSpec("reverse:https://example.com:8085@localhost:8082"),
        );
        expect(parsed).toEqual({
            active: true,
            ui_id: parsed.ui_id,
            protocol: ReverseProxyProtocols.HTTPS,
            destination: "example.com:8085",
            listen_host: "localhost",
            listen_port: 8082,
        } as ReverseState);
    });
});
