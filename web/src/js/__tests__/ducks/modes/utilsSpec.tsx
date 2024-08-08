import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "../tutils";
import {
    isActiveMode,
    parseSpec,
    updateModeInner,
} from "../../../ducks/modes/utils";
import { includeListenAddress } from "../../../modes";
import { ModesState } from "../../../ducks/modes";
import { getSpec as getRegularSpec } from "../../../modes/regular";
import { getSpec as getReverseSpec } from "../../../modes/reverse";
import { getSpec as getWireguardSpec } from "../../../modes/wireguard";
import { getSpec as getLocalSpec } from "../../../modes/local";
import { ReverseProxyProtocols } from "../../../backends/consts";

enableFetchMocks();

describe("updateMode action creator", () => {
    beforeEach(() => {
        fetchMock.resetMocks();
    });

    it("should call updateMode method with a successful api call", async () => {
        const store = TStore();
        fetchMock.mockResponseOnce(JSON.stringify({ success: true }));

        await store.dispatch(() => updateModeInner(store.getState().modes));

        const expectedUrl = "./options";
        const expectedBody = JSON.stringify({ mode: ["regular"] });

        const actualCall = fetchMock.mock.calls[0];
        const actualUrl = actualCall[0];
        const actualBody = actualCall[1]?.body;

        expect(actualUrl).toEqual(expectedUrl);
        expect(actualBody).toEqual(expectedBody);
    });

    it("fetch HTTP status != 200 throws", async () => {
        const store = TStore();
        fetchMock.mockResponseOnce("invalid query", { status: 400 });
        await expect(
            TStore().dispatch(() => updateModeInner(store.getState().modes)),
        ).rejects.toThrow("invalid query");
    });

    it("fetch error throws", async () => {
        const store = TStore();
        fetchMock.mockRejectOnce(new Error("network error"));
        await expect(
            TStore().dispatch(() => updateModeInner(store.getState().modes)),
        ).rejects.toThrow("network error");
    });
});

describe("includeListenAddress", () => {
    it("should keep mode as-is if not port is specified", () => {
        const mode = {};
        const result = includeListenAddress("regular", mode);
        expect(result).toEqual("regular");
    });

    it("should return array with mode name and listen_port if mode is active with listen_port", () => {
        const mode = {
            listen_port: 8080,
        };
        const result = includeListenAddress("regular", mode);
        expect(result).toEqual("regular@8080");
    });

    it("should return array with mode name, listen_host, and listen_port if mode is active with listen_host and listen_port", () => {
        const mode = {
            listen_host: "localhost",
            listen_port: 8080,
        };
        const result = includeListenAddress("regular", mode);
        expect(result).toEqual("regular@localhost:8080");
    });
});

describe("isActiveMode", () => {
    it("should work", () => {
        expect(isActiveMode({ active: false })).toBe(false);
        expect(isActiveMode({ active: true })).toBe(true);
        expect(isActiveMode({ active: true, error: "failed" })).toBe(false);
        expect(isActiveMode({ active: false, error: "failed" })).toBe(false);
    });
});

describe("parseMode", () => {
    it("should parse regular mode with host and port", () => {
        const modeConfig = "regular@localhost:8081";
        const result = parseSpec(modeConfig);
        expect(result).toEqual({
            name: "regular",
            full_spec: "regular@localhost:8081",
            data: "",
            listen_host: "localhost",
            listen_port: 8081,
        });
    });

    it("should parse local mode with data", () => {
        const modeConfig = "local:curl,http";
        const result = parseSpec(modeConfig);
        expect(result).toEqual({
            name: "local",
            data: "curl,http",
            full_spec: "local:curl,http",
            listen_host: undefined,
            listen_port: undefined,
        });
    });

    it("should throw an error for invalid port", () => {
        const modeConfig = "regular@99999";
        expect(() => parseSpec(modeConfig)).toThrow("invalid port: 99999");
    });
});

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
        const mode = getRegularSpec(modes.regular[0]);
        expect(mode).toBe("regular@localhost:8082");
    });
});

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
        const mode = getReverseSpec(modes.reverse[0]);
        expect(mode).toBe("reverse:https://example.com:8085@localhost:8082");
    });
});

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
        const mode = getWireguardSpec(modes.wireguard[0]);
        expect(mode).toBe("wireguard@localhost:8082");
    });
});

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
        const mode = getLocalSpec(modes.local[0]);
        expect(mode).toBe("local:curl,http");
    });
});
