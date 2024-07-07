import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "../tutils";
import {
    includeModeState,
    parseMode,
    updateMode,
} from "../../../ducks/modes/utils";

enableFetchMocks();

describe("updateMode action creator", () => {
    beforeEach(() => {
        fetchMock.resetMocks();
    });

    it("should call updateMode method with a successful api call", async () => {
        const store = TStore();
        fetchMock.mockResponseOnce(JSON.stringify({ success: true }));

        await store.dispatch(updateMode());

        const expectedUrl = "./options";
        const expectedBody = JSON.stringify({ mode: ["regular"] });

        const actualCall = fetchMock.mock.calls[0];
        const actualUrl = actualCall[0];
        const actualBody = actualCall[1]?.body;

        expect(actualUrl).toEqual(expectedUrl);
        expect(actualBody).toEqual(expectedBody);
    });

    it("fetch HTTP status != 200 throws", async () => {
        fetchMock.mockResponseOnce("invalid query", { status: 400 });
        await expect(TStore().dispatch(updateMode())).rejects.toThrow(
            "invalid query",
        );
    });

    it("fetch error throws", async () => {
        fetchMock.mockRejectOnce(new Error("network error"));
        await expect(TStore().dispatch(updateMode())).rejects.toThrow(
            "network error",
        );
    });
});

describe("includeModeState", () => {
    it("should return array with mode name and listen_port if mode is active with listen_port", () => {
        const mode = {
            active: true,
            listen_port: 8080,
        };
        const result = includeModeState("regular", mode);
        expect(result).toEqual(["regular@8080"]);
    });

    it("should return array with mode name, listen_host, and listen_port if mode is active with listen_host and listen_port", () => {
        const mode = {
            active: true,
            listen_host: "localhost",
            listen_port: 8080,
        };
        const result = includeModeState("regular", mode);
        expect(result).toEqual(["regular@localhost:8080"]);
    });

    it("should return array with mode name and listen_host if mode is active with listen_host and no listen_port", () => {
        const mode = {
            name: "regular",
            active: true,
            listen_host: "localhost",
        };
        const result = includeModeState("regular", mode);
        expect(result).toEqual(["regular"]);
    });

    it("should return an empty array if there is a ui_error", () => {
        const mode = {
            active: false,
            listen_host: "localhost",
            listen_port: 8080,
            error: "error message",
        };
        const result = includeModeState("regular", mode);
        expect(result).toEqual([]);
    });
});

describe("parseMode", () => {
    it("should parse regular mode with host and port", () => {
        const modeConfig = "regular@localhost:8081";
        const result = parseMode(modeConfig);
        expect(result).toEqual({
            name: "regular",
            data: "",
            listen_host: "localhost",
            listen_port: 8081,
        });
    });

    it("should parse local mode with data", () => {
        const modeConfig = "local:curl,http";
        const result = parseMode(modeConfig);
        expect(result).toEqual({
            name: "local",
            data: "curl,http",
            listen_host: "",
            listen_port: "",
        });
    });

    it("should throw an error for invalid port", () => {
        const modeConfig = "regular@99999";
        expect(() => parseMode(modeConfig)).toThrow("invalid port: 99999");
    });
});
