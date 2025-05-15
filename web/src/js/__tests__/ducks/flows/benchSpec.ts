import { TFlow } from "../tutils";

import flowReducer, {
    defaultState,
    FLOWS_ADD,
    FLOWS_RECEIVE,
} from "../../../ducks/flows";

// Mini benchmark for redux performance.
// Main findings:
//  - Immer is terrible performance-wise.
//  - No major difference between Map and object.

// Increase for manual testing
const N = 100;

test("receive", () => {
    const flows = new Array(N).fill(undefined).map(() => TFlow());

    console.time(`receive ${N} flows`);
    let state = flowReducer(defaultState, FLOWS_RECEIVE(flows));
    console.timeEnd(`receive ${N} flows`);
    expect(state.view.length).toBe(N);
});

test("add", () => {
    const actions = new Array(N)
        .fill(undefined)
        .map(() => FLOWS_ADD({ flow: TFlow(), matching_filters: {} }));

    let state = defaultState;
    console.time(`add ${N} flows`);
    for (const action of actions) {
        state = flowReducer(state, action);
    }
    console.timeEnd(`add ${N} flows`);
    expect(state.view.length).toBe(N);
});
