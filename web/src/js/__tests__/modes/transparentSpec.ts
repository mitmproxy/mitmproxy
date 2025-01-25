import { ModesState } from "../../ducks/modes";
import { parseSpec } from "../../modes";
import { getSpec, parseRaw, TransparentState } from "../../modes/transparent";

describe("getSpec transparent mode", () => {
    it("should return the correct mode config", () => {
        const modes = {
            transparent: [
                {
                    active: true,
                    listen_host: "localhost",
                    listen_port: 8082,
                },
            ],
        } as ModesState;
        const mode = getSpec(modes.transparent[0]);
        expect(mode).toBe("transparent@localhost:8082");
    });
});

describe("parseRaw transparent mode", () => {
    it("should parse", () => {
        const parsed = parseRaw(parseSpec("transparent@localhost:8082"));
        expect(parsed).toEqual({
            active: true,
            ui_id: parsed.ui_id,
            listen_host: "localhost",
            listen_port: 8082,
        } as TransparentState);
    });
});
