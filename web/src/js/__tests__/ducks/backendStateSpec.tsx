import reduceBackendState, {
    defaultState,
    STATE_RECEIVE,
    STATE_UPDATE,
} from "../../ducks/backendState";
import { TBackendState } from "./_tbackendstate";

test("backendState", async () => {
    let state = reduceBackendState(undefined, { type: "other" });
    expect(state).toEqual(defaultState);

    state = reduceBackendState(undefined, STATE_RECEIVE(TBackendState()));
    expect(state.version).toBe("1.2.3");

    state = reduceBackendState(undefined, STATE_UPDATE({ version: "42.0" }));
    expect(state.version).toBe("42.0");
});
