import { ModesState } from "../../ducks/modes";
import { parseSpec } from "../../modes";
import { getSpec, parseRaw, UpstreamState } from "../../modes/upstream";

describe("getSpec upstream mode", () => {
    it("should return the correct mode config", () => {
        const modes = {
            upstream: [
                {
                    active: true,
                    destination: "https://example.com:8085",
                    listen_host: "localhost",
                    listen_port: 8082,
                },
            ],
        } as ModesState;
        const mode = getSpec(modes.upstream[0]);
        expect(mode).toBe("upstream:https://example.com:8085@localhost:8082");
    });
});

describe("parseRaw upstream mode", () => {
    it("should parse", () => {
        const parsed = parseRaw(
            parseSpec("upstream:https://example.com:8085@localhost:8082"),
        );
        expect(parsed).toEqual({
            active: true,
            ui_id: parsed.ui_id,
            destination: "https://example.com:8085",
            listen_host: "localhost",
            listen_port: 8082,
        } as UpstreamState);
    });
});
