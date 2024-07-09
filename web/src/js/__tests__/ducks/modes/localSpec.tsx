import localReducer, {
    getMode,
    initialState,
    setApplications,
    toggleLocal,
} from "../../../ducks/modes/local";
import { ModesState } from "../../../ducks/modes";
import { toggleRegular } from "../../../ducks/modes/regular";
import * as backendState from "../../../ducks/backendState";
import { TStore } from "../tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

describe("localReducer", () => {
    it("should return the initial state", () => {
        const state = localReducer(undefined, {});
        expect(state).toEqual(initialState);
    });

    it("should dispatch MODE_LOCAL_TOGGLE and updateMode", async () => {
        enableFetchMocks();

        const store = TStore();

        expect(store.getState().modes.local.active).toBe(false);
        await store.dispatch(toggleLocal());
        expect(store.getState().modes.local.active).toBe(true);
        expect(fetchMock).toHaveBeenCalled();
    });

    it("should dispatch MODE_LOCAL_SET_APPLICATIONS and updateMode", async () => {
        enableFetchMocks();
        const store = TStore();

        await store.dispatch(setApplications("curl"));

        const state = store.getState().modes.local;
        expect(state.applications).toEqual("curl");
        expect(fetchMock).toHaveBeenCalled();
    });

    it('should handle UPDATE_STATE action with data.mode not containing "local"', async () => {
        const store = TStore();

        await store.dispatch(setApplications("curl"));

        await store.dispatch(toggleRegular());

        expect(store.getState().modes.local.active).toBe(false);
        expect(store.getState().modes.regular.active).toBe(false);
        expect(store.getState().modes.local.applications).toBe("curl");
    });

    it('should handle RECEIVE_STATE action with data.servers containing "local" and an application', () => {
        const action = {
            type: backendState.RECEIVE,
            data: {
                servers: [
                    {
                        type: "local",
                        description: "Local redirector",
                        full_spec: "local:curl",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [],
                    },
                ],
            },
        };
        const newState = localReducer(undefined, action);
        expect(newState.active).toBe(true);
        expect(newState.applications).toBe("curl");
        expect(newState.error).toBeUndefined();
    });

    it('should handle RECEIVE_STATE action with data.servers containing "local"', () => {
        const initialState = {
            active: false,
            applications: "curl",
        };
        const action = {
            type: backendState.RECEIVE,
            data: {
                servers: [
                    {
                        type: "local",
                        description: "Local redirector",
                        full_spec: "local",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [],
                    },
                ],
            },
        };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(true);
        expect(newState.applications).toBe("");
        expect(newState.error).toBeUndefined();
    });

    it("should handle RECEIVE_OPTIONS action with data.servers containing another mode", () => {
        const initialState = {
            active: false,
            applications: "curl",
        };
        const action = {
            type: backendState.RECEIVE,
            data: {
                servers: [
                    {
                        description: "HTTP(S) proxy",
                        full_spec: "regular@localhost:8081",
                        is_running: true,
                        last_exception: null,
                        listen_addrs: [
                            ["127.0.0.1", 8081],
                            ["::1", 8081],
                        ],
                        type: "regular",
                    },
                ],
            },
        };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(false);
        expect(newState.applications).toBe(initialState.applications);
    });

    it("should handle RECEIVE_OPTIONS action without data.servers", () => {
        const initialState = {
            active: false,
            applications: "curl",
        };
        const action = {
            type: backendState.RECEIVE,
            data: {},
        };
        const newState = localReducer(initialState, action);
        expect(newState.active).toBe(initialState.active);
        expect(newState.applications).toBe(initialState.applications);
    });

    it("should handle error when toggling local", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(toggleLocal());

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.local.error).toBe("invalid spec");
    });

    it("should handle error when setting applications", async () => {
        fetchMock.mockReject(new Error("invalid spec"));
        const store = TStore();

        await store.dispatch(setApplications("invalid,,"));

        expect(fetchMock).toHaveBeenCalled();
        expect(store.getState().modes.local.error).toBe("invalid spec");
    });
});

describe("getMode", () => {
    it("should return local mode with applications when active and applications are present", () => {
        const modes = {
            local: {
                active: true,
                applications: "curl",
            },
        } as ModesState;
        const result = getMode(modes);
        expect(result).toEqual(["local:curl"]);
    });

    it("should return local mode without applications when active and no applications are present", () => {
        const modes = {
            local: {
                active: true,
                applications: "",
            },
        } as ModesState;
        const result = getMode(modes);
        expect(result).toEqual(["local"]);
    });

    it("should return an empty array when local mode is not active", () => {
        const modes = {
            local: {
                active: false,
                applications: "curl",
            },
        } as ModesState;
        const result = getMode(modes);
        expect(result).toEqual([]);
    });

    it("should return an empty string when there is a ui error", () => {
        const modes = {
            local: {
                active: false,
                listen_host: "localhost",
                listen_port: 8080,
                error: "error local mode",
            },
        } as ModesState;
        const mode = getMode(modes);
        expect(JSON.stringify(mode)).toBe(JSON.stringify([]));
    });
});
