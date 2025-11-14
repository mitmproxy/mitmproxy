import type { ModesState } from "../../ducks/modes";
import { parseSpec } from "../../modes";
import type { DnsState } from "../../modes/dns";
import { getSpec, parseRaw } from "../../modes/dns";

describe("getSpec dns mode", () => {
    it("should return the correct mode config", () => {
        const modes = {
            dns: [
                {
                    active: true,
                    listen_host: "localhost",
                    listen_port: 8082,
                },
            ],
        } as ModesState;
        const mode = getSpec(modes.dns[0]);
        expect(mode).toBe("dns@localhost:8082");
    });
});

describe("parseRaw dns mode", () => {
    it("should parse", () => {
        const parsed = parseRaw(parseSpec("dns@localhost:8082"));
        expect(parsed).toEqual({
            active: true,
            ui_id: parsed.ui_id,
            listen_host: "localhost",
            listen_port: 8082,
        } as DnsState);
    });
});
