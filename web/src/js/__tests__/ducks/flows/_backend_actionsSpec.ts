import { TFlow, TStore, TTCPFlow } from "../tutils";
import * as flowActions from "../../../ducks/flows";
import { fetchApi } from "../../../utils";

jest.mock("../../../utils");

describe("flows actions", () => {
    const store = TStore();
    const tflow = TFlow();
    tflow.intercepted = true;
    tflow.modified = true;
    // @ts-expect-error TFlow is Required<> for other tests.
    tflow.websocket = undefined;
    const ttcpflow = TTCPFlow();

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it("should handle resume action", () => {
        store.dispatch(flowActions.resume([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/resume",
            { method: "POST" },
        );
    });

    it("should handle resumeAll action", () => {
        store.dispatch(flowActions.resumeAll());
        expect(fetchApi).toBeCalledWith("/flows/resume", { method: "POST" });
    });

    it("should handle kill action", () => {
        store.dispatch(flowActions.kill([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/kill",
            { method: "POST" },
        );
    });

    it("should handle killAll action", () => {
        store.dispatch(flowActions.killAll());
        expect(fetchApi).toBeCalledWith("/flows/kill", { method: "POST" });
    });

    it("should handle remove action", () => {
        store.dispatch(flowActions.remove([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29",
            { method: "DELETE" },
        );
    });

    it("should handle remove action with multiple flows", async () => {
        await store.dispatch(flowActions.remove([tflow, ttcpflow]));

        expect(fetchApi).toHaveBeenCalledTimes(2);
        expect(fetchApi).toHaveBeenCalledWith(`/flows/${tflow.id}`, {
            method: "DELETE",
        });
        expect(fetchApi).toHaveBeenCalledWith(`/flows/${ttcpflow.id}`, {
            method: "DELETE",
        });
    });

    it("should handle duplicate action", () => {
        store.dispatch(flowActions.duplicate([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/duplicate",
            { method: "POST" },
        );
    });

    it("should handle replay action", () => {
        store.dispatch(flowActions.replay([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/replay",
            { method: "POST" },
        );
    });

    it("should handle revert action", () => {
        store.dispatch(flowActions.revert([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/revert",
            { method: "POST" },
        );
    });

    it("should handle mark action", async () => {
        store.dispatch(flowActions.mark([tflow, ttcpflow], ":red_circle:"));
        expect(fetchApi.put).toHaveBeenCalledWith(`/flows/${tflow.id}`, {
            marked: ":red_circle:",
        });
        expect(fetchApi.put).toHaveBeenCalledWith(`/flows/${ttcpflow.id}`, {
            marked: ":red_circle:",
        });
    });

    it("should handle update action", () => {
        store.dispatch(flowActions.update(tflow, "foo"));
        expect(fetchApi.put).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29",
            "foo",
        );
    });

    it("should handle uploadContent action", () => {
        const body = new FormData();
        const file = new window.Blob(["foo"], { type: "plain/text" });
        body.append("file", file);
        store.dispatch(flowActions.uploadContent(tflow, "foo", "foo"));
        // window.Blob's lastModified is always the current time,
        // which causes flaky tests on comparison.
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/foo/content.data",
            {
                method: "POST",
                body: expect.anything(),
            },
        );
    });

    it("should handle clear action", () => {
        store.dispatch(flowActions.clear());
        expect(fetchApi).toBeCalledWith("/clear", { method: "POST" });
    });

    it("should handle upload action", () => {
        const body = new FormData();
        body.append("file", "foo");
        store.dispatch(flowActions.upload("foo"));
        expect(fetchApi).toBeCalledWith("/flows/dump", {
            method: "POST",
            body,
        });
    });
});
