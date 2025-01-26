import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "./tutils";
import { fetchProcesses } from "../../ducks/processes";

describe("processesSlice", () => {
    beforeEach(() => {
        enableFetchMocks();
        fetchMock.resetMocks();
    });

    it("should handle fetchProcesses pending state", async () => {
        fetchMock.mockResponseOnce(() => new Promise(() => {}));

        const store = TStore();

        store.dispatch(fetchProcesses());
        expect(store.getState().processes.isLoading).toBe(true);
    });

    it("should handle fetchProcesses fulfilled state", async () => {
        const mockProcesses = [
            {
                is_visible: true,
                executable: "curl.exe",
                is_system: "false",
                display_name: "curl",
            },
            {
                is_visible: true,
                executable: "http.exe",
                is_system: "false",
                display_name: "http",
            },
        ];

        fetchMock.mockResponseOnce(JSON.stringify(mockProcesses));

        const store = TStore();

        await store.dispatch(fetchProcesses());

        expect(store.getState().processes.isLoading).toBe(false);
        expect(store.getState().processes.currentProcesses).toEqual(
            mockProcesses,
        );
        expect(fetchMock).toHaveBeenCalledWith("./processes", {
            credentials: "same-origin",
        });
    });

    it("should handle fetchProcesses rejected state", async () => {
        fetchMock.mockReject(new Error("Failed to fetch processes"));
        const store = TStore();

        await store.dispatch(fetchProcesses());

        expect(store.getState().processes.isLoading).toBe(false);
        expect(store.getState().processes.error).toBe(
            "Failed to fetch processes",
        );
        expect(fetchMock).toHaveBeenCalledWith("./processes", {
            credentials: "same-origin",
        });
    });
});
