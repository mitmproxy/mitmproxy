import reduceEventLog, * as eventLogActions from "../../ducks/eventLog";
import {
    add,
    defaultState,
    EVENTS_RECEIVE,
    LogLevel,
} from "../../ducks/eventLog";

describe("event log reducer", () => {
    it("should be possible to toggle filter", () => {
        const state = reduceEventLog(
            defaultState,
            eventLogActions.add("foo", LogLevel.info),
        );
        expect(
            reduceEventLog(state, eventLogActions.toggleFilter(LogLevel.info)),
        ).toEqual({
            ...state,
            view: [],
            filters: { ...state.filters, info: false },
        });
    });

    it("should be possible to toggle visibility", () => {
        expect(
            reduceEventLog(defaultState, eventLogActions.toggleVisibility())
                .visible,
        ).toBe(true);
    });

    it("should be possible to add message", () => {
        let state = defaultState;
        state = reduceEventLog(state, eventLogActions.add("foo"));
        state = reduceEventLog(
            state,
            eventLogActions.add("bar", LogLevel.debug),
        );
        const foo = {
            message: "foo",
            level: LogLevel.web,
            id: state.list[0].id,
        };
        const bar = {
            message: "bar",
            level: LogLevel.debug,
            id: state.list[1].id,
        };
        expect(state).toEqual({
            ...state,
            list: [foo, bar],
            view: [foo],
        });
    });

    it("should receive state", () => {
        const state = reduceEventLog(
            undefined,
            eventLogActions.EVENTS_RECEIVE([
                {
                    message: "hello",
                    level: LogLevel.info,
                    id: "123",
                },
                {
                    message: "world",
                    level: LogLevel.debug,
                    id: "456",
                },
            ]),
        );
        expect(state.list.length).toBe(2);
        expect(state.view.length).toBe(1);
    });
});

// Mini benchmark for redux performance.
// Main findings:
//  - Immer is terrible performance-wise.

// Increase for manual testing
const N = 1000;

test("receive", () => {
    const events = new Array(N).fill(undefined).map(() => add("test").payload);

    console.time(`receive ${N} events`);
    let state = reduceEventLog(defaultState, EVENTS_RECEIVE(events));
    console.timeEnd(`receive ${N} events`);
    expect(state.view.length).toBe(N);
});

test("add", () => {
    const actions = new Array(N).fill(undefined).map(() => add("test"));

    let state = defaultState;
    console.time(`add ${N} events`);
    for (const action of actions) {
        state = reduceEventLog(state, action);
    }
    console.timeEnd(`add ${N} events`);
    expect(state.view.length).toBe(N);
});
