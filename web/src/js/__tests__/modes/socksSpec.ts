import { ModesState } from "../../ducks/modes";
import { parseSpec } from "../../modes";
import { getSpec, parseRaw, SocksState } from "../../modes/socks";

describe("getSpec socks mode", () => {
    it("should return the correct mode config", () => {
        const modes = {
            socks: [
                {
                    active: true,
                    listen_host: "localhost",
                    listen_port: 8082,
                },
            ],
        } as ModesState;
        const mode = getSpec(modes.socks[0]);
        expect(mode).toBe("socks5@localhost:8082");
    });
});

describe("parseRaw socks mode", () => {
    it("should parse", () => {
        const parsed = parseRaw(parseSpec("socks5@localhost:8082"));
        expect(parsed).toEqual({
            active: true,
            ui_id: parsed.ui_id,
            listen_host: "localhost",
            listen_port: 8082,
        } as SocksState);
    });
});
