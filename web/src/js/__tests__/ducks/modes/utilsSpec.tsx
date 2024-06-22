import { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "../tutils";
import { fetchApi } from "../../../utils";
import { addListenAddr, updateMode } from "../../../ducks/modes/utils";
import { parseMode } from "../../../ducks/modes/utils";

enableFetchMocks();

jest.mock("../../../utils", () => ({
    fetchApi: {
        put: jest.fn(),
    },
}));

describe("updateMode action creator", () => {
    beforeEach(() => {
        fetchMock.resetMocks();
    });

    it("should call updateMode method with a successful api call", async () => {
        const store = TStore();
        (fetchApi.put as jest.Mock).mockResolvedValueOnce({ status: 200 });

        await store.dispatch(updateMode());

        expect(fetchApi.put).toBeCalledWith("/options", {
            mode: ["regular"],
        });
    });
});

describe("addListenAddr", () => {
    it("should return array with mode name and listen_port if mode is active with listen_port", () => {
        const mode = {
            name: "regular",
            active: true,
            listen_port: 8080,
        };
        const result = addListenAddr(mode);
        expect(result).toEqual(["regular@8080"]);
    });

    it("should return array with mode name, listen_host, and listen_port if mode is active with listen_host and listen_port", () => {
        const mode = {
            name: "regular",
            active: true,
            listen_host: "localhost",
            listen_port: 8080,
        };
        const result = addListenAddr(mode);
        expect(result).toEqual(["regular@localhost:8080"]);
    });

    it("should return array with mode name and listen_host if mode is active with listen_host and no listen_port", () => {
        const mode = {
            name: "regular",
            active: true,
            listen_host: "localhost",
        };
        const result = addListenAddr(mode);
        expect(result).toEqual(["regular"]);
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
