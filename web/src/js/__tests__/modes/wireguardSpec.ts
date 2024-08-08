import { ModesState } from "../../ducks/modes";
import { parseSpec } from "../../modes";
import { getSpec, parseRaw, WireguardState } from "../../modes/wireguard";

describe("getSpec wireguard mode", () => {
    it("should return the correct mode config", () => {
        const modes = {
            wireguard: [
                {
                    active: true,
                    listen_host: "localhost",
                    listen_port: 8082,
                },
            ],
        } as ModesState;
        const mode = getSpec(modes.wireguard[0]);
        expect(mode).toBe("wireguard@localhost:8082");
    });
});

describe("parseRaw wireguard mode", () => {
    it("should parse", () => {
        const parsed = parseRaw(parseSpec("wireguard@localhost:8082"));
        expect(parsed).toEqual({
            active: true,
            ui_id: parsed.ui_id,
            file_path: "",
            listen_host: "localhost",
            listen_port: 8082,
        } as WireguardState);
    });
});
