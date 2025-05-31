import reduceConnection, * as ConnectionActions from "../../ducks/connection";
import { ConnectionState } from "../../ducks/connection";

describe("connection reducer", () => {
    it("should return initial state", () => {
        expect(reduceConnection(undefined, { type: "other" })).toEqual({
            state: ConnectionState.INIT,
            message: undefined,
        });
    });

    it("should handle start fetch", () => {
        expect(
            reduceConnection(undefined, ConnectionActions.startFetching()),
        ).toEqual({
            state: ConnectionState.FETCHING,
            message: undefined,
        });
    });

    it("should handle connection established", () => {
        expect(
            reduceConnection(
                {
                    state: ConnectionState.FETCHING,
                    message: undefined,
                },
                ConnectionActions.finishFetching(),
            ),
        ).toEqual({
            state: ConnectionState.ESTABLISHED,
            message: undefined,
        });
        expect(
            reduceConnection(
                {
                    state: ConnectionState.ERROR,
                    message: "we already failed",
                },
                ConnectionActions.finishFetching(),
            ),
        ).toEqual({
            state: ConnectionState.ERROR,
            message: "we already failed",
        });
    });

    it("should handle connection error", () => {
        expect(
            reduceConnection(
                undefined,
                ConnectionActions.connectionError("no internet"),
            ),
        ).toEqual({
            state: ConnectionState.ERROR,
            message: "no internet",
        });
    });
});
