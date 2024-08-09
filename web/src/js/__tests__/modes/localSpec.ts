import { ModesState } from "../../ducks/modes";
import { parseSpec } from "../../modes";
import { getSpec, LocalState, parseRaw } from "../../modes/local";

describe("getSpec local mode", () => {
    it("should return the correct mode config", () => {
        const modes = {
            local: [
                {
                    active: true,
                    applications: "curl,http",
                },
            ],
        } as ModesState;
        const mode = getSpec(modes.local[0]);
        expect(mode).toBe("local:curl,http");
    });
});

describe("parseRaw local mode", () => {
    it("should parse", () => {
        const parsed = parseRaw(parseSpec("local:curl,http"));
        expect(parsed).toEqual({
            active: true,
            ui_id: parsed.ui_id,
            applications: "curl,http",
        } as LocalState);
    });
});
