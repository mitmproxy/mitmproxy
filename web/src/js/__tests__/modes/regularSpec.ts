import { ModesState } from "../../ducks/modes";
import { parseSpec } from "../../modes";
import { getSpec, parseRaw, RegularState } from "../../modes/regular";

describe("getSpec regular mode", () => {
    it("should return the correct mode config", () => {
        const modes = {
            regular: [
                {
                    active: true,
                    listen_host: "localhost",
                    listen_port: 8082,
                },
            ],
        } as ModesState;
        const mode = getSpec(modes.regular[0]);
        expect(mode).toBe("regular@localhost:8082");
    });
});

describe("parseRaw regular mode", () => {
    it("should parse", () => {
        const parsed = parseRaw(parseSpec("regular@localhost:8082"));
        expect(parsed).toEqual({
            active: true,
            ui_id: parsed.ui_id,
            listen_host: "localhost",
            listen_port: 8082,
        } as RegularState);
    });
});
