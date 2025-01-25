import { includeListenAddress, parseSpec } from "../../modes";

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

describe("parseSpec", () => {
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
