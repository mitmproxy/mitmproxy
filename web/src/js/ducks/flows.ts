import { fetchApi } from "../utils";

import * as store from "./utils/store";
import Filt from "../filt/filt";
import { Flow } from "../flow";
import {
    canReplay,
    canResumeOrKill,
    canRevert,
    sortFunctions,
} from "../flow/utils";
import { AppDispatch, RootState } from "./store";
import { State } from "./utils/store";
import {
    Action,
    createAction,
    createSlice,
    PayloadAction,
} from "@reduxjs/toolkit";

export const FLOWS_ADD = createAction<Flow>("FLOWS_ADD");
export const FLOWS_UPDATE = createAction<Flow>("FLOWS_UPDATE");
export const FLOWS_REMOVE = createAction<string>("FLOWS_REMOVE");
export const FLOWS_RECEIVE = createAction<Flow[]>("FLOWS_RECEIVE");

interface FlowSortFn extends store.SortFn<Flow> {}

interface FlowFilterFn extends store.FilterFn<Flow> {}

export interface FlowsState extends store.State<Flow> {
    highlight?: string;
    filter?: string;
    sort: { column?: keyof typeof sortFunctions; desc: boolean };
    selected: Flow[];
    selectedIndex: { [id: string]: number };
}

export const defaultState: FlowsState = {
    highlight: undefined,
    filter: undefined,
    sort: { column: undefined, desc: false },
    selected: [],
    selectedIndex: {},
    ...store.defaultState,
};

function updateSelected(
    state: FlowsState = defaultState,
    newStoreState: State<Flow>,
    action: Action,
): Pick<FlowsState, "selected" | "selectedIndex"> {
    let { selected, selectedIndex } = state;
    if (FLOWS_UPDATE.match(action)) {
        if (selectedIndex[action.payload.id] !== undefined) {
            selected = selected.map((f) =>
                f.id === action.payload.id ? action.payload : f,
            );
        }
    } else if (FLOWS_RECEIVE.match(action)) {
        selected = selected
            .map((f) => newStoreState.byId[f.id])
            .filter((f) => f !== undefined);
        selectedIndex = Object.fromEntries(selected.map((f, i) => [f.id, i]));
    } else if (FLOWS_REMOVE.match(action)) {
        if (selectedIndex[action.payload] !== undefined) {
            if (selected.length > 1) {
                selected = selected.filter((f) => f.id !== action.payload);
            } else if (!(action.payload in state.viewIndex)) {
                selected = [];
            } else {
                const currentIndex = state.viewIndex[action.payload];
                // Try to select the next item in view, or fallback to the previous one
                const fallback =
                    state.view[currentIndex + 1] ??
                    state.view[currentIndex - 1]; // last element
                // If fallback is undefined (e.g. removed last remaining flow)
                selected = fallback ? [fallback] : [];
            }
            selectedIndex = Object.fromEntries(
                selected.map((f, i) => [f.id, i]),
            );
        }
    }
    return { selected, selectedIndex };
}

const flowsSlice = createSlice({
    name: "flows",
    initialState: defaultState,
    reducers: {
        setFilter: (state, action: PayloadAction<string>) => {
            const newStoreState = store.reduce(
                state,
                store.setFilter(
                    makeFilter(action.payload),
                    makeSort(state.sort),
                ),
            );
            return {
                ...state,
                filter: action.payload,
                ...newStoreState,
            };
        },
        setHighlight: (state, action: PayloadAction<string>) => {
            return {
                ...state,
                highlight: action.payload,
            };
        },
        setSort: (
            state,
            action: PayloadAction<{
                column?: keyof typeof sortFunctions;
                desc: boolean;
            }>,
        ) => {
            const newStoreState = store.reduce(
                state,
                store.setSort(makeSort(action.payload)),
            );
            return {
                ...state,
                sort: action.payload,
                ...newStoreState,
            };
        },
        select: (state, action: PayloadAction<Flow[]>) => {
            return {
                ...state,
                selected: action.payload,
                selectedIndex: Object.fromEntries(
                    action.payload.map((f, i) => [f.id, i]),
                ),
            };
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(FLOWS_ADD, (state, action) => {
                const newStoreState = store.reduce(
                    state,
                    store.add(
                        action.payload,
                        makeFilter(state.filter),
                        makeSort(state.sort),
                    ),
                );
                return {
                    ...state,
                    ...newStoreState,
                };
            })
            .addCase(FLOWS_UPDATE, (state, action) => {
                const newStoreState = store.reduce(
                    state,
                    store.update(
                        action.payload,
                        makeFilter(state.filter),
                        makeSort(state.sort),
                    ),
                );
                return {
                    ...state,
                    ...newStoreState,
                    ...updateSelected(state, newStoreState, action),
                };
            })
            .addCase(FLOWS_REMOVE, (state, action) => {
                const newStoreState = store.reduce(
                    state,
                    store.remove(action.payload),
                );
                return {
                    ...state,
                    ...newStoreState,
                    ...updateSelected(state, newStoreState, action),
                };
            })
            .addCase(FLOWS_RECEIVE, (state, action) => {
                const newStoreState = store.reduce(
                    state,
                    store.receive(
                        action.payload,
                        makeFilter(state.filter),
                        makeSort(state.sort),
                    ),
                );
                return {
                    ...state,
                    ...newStoreState,
                    ...updateSelected(state, newStoreState, action),
                };
            });
    },
});

export const { setFilter, setHighlight, setSort, select } = flowsSlice.actions;

export function makeFilter(filter?: string): FlowFilterFn | undefined {
    if (!filter) {
        return;
    }
    return Filt.parse(filter);
}

export function makeSort({
    column,
    desc,
}: {
    column?: keyof typeof sortFunctions;
    desc: boolean;
}): FlowSortFn {
    if (!column) {
        return (_a, _b) => 0;
    }
    const sortKeyFun = sortFunctions[column];
    return (a, b) => {
        const ka = sortKeyFun(a);
        const kb = sortKeyFun(b);
        // @ts-expect-error undefined is fine
        if (ka > kb) {
            return desc ? -1 : 1;
        }
        // @ts-expect-error undefined is fine
        if (ka < kb) {
            return desc ? 1 : -1;
        }
        return 0;
    };
}

export function selectRelative(flows: FlowsState, shift: number) {
    const currentSelectionIndex: number | undefined =
        flows.viewIndex[flows.selected[flows.selected.length - 1]?.id];
    const minIndex = 0;
    const maxIndex = flows.view.length - 1;
    let newIndex: number;
    if (currentSelectionIndex === undefined) {
        newIndex = shift < 0 ? minIndex : maxIndex;
    } else {
        newIndex = currentSelectionIndex + shift;
        newIndex = window.Math.max(newIndex, minIndex);
        newIndex = window.Math.min(newIndex, maxIndex);
    }
    const flow = flows.view[newIndex];
    return select(flow ? [flow] : []);
}

export function resume(flows: Flow[]) {
    flows = flows.filter(canResumeOrKill);
    return () =>
        Promise.all(
            flows.map((flow) =>
                fetchApi(`/flows/${flow.id}/resume`, { method: "POST" }),
            ),
        );
}

export function resumeAll() {
    return () => fetchApi("/flows/resume", { method: "POST" });
}

export function kill(flows: Flow[]) {
    flows = flows.filter(canResumeOrKill);
    return () =>
        Promise.all(
            flows.map((flow) =>
                fetchApi(`/flows/${flow.id}/kill`, { method: "POST" }),
            ),
        );
}

export function killAll() {
    return () => fetchApi("/flows/kill", { method: "POST" });
}

export function remove(flows: Flow[]) {
    return () =>
        Promise.all(
            flows.map((flow) =>
                fetchApi(`/flows/${flow.id}`, { method: "DELETE" }),
            ),
        );
}

export function duplicate(flows: Flow[]) {
    return () =>
        Promise.all(
            flows.map((flow) =>
                fetchApi(`/flows/${flow.id}/duplicate`, { method: "POST" }),
            ),
        );
}

export function replay(flows: Flow[]) {
    flows = flows.filter(canReplay);
    return () =>
        Promise.all(
            flows.map((flow) =>
                fetchApi(`/flows/${flow.id}/replay`, { method: "POST" }),
            ),
        );
}

export function revert(flows: Flow[]) {
    flows = flows.filter(canRevert);
    return () =>
        Promise.all(
            flows.map((flow) =>
                fetchApi(`/flows/${flow.id}/revert`, { method: "POST" }),
            ),
        );
}

export function mark(flows: Flow[], marked: string) {
    return () => Promise.all(flows.map((flow) => update(flow, { marked })()));
}

export function update(flow: Flow, data) {
    return () => fetchApi.put(`/flows/${flow.id}`, data);
}

export function uploadContent(flow: Flow, file, type) {
    const body = new FormData();
    file = new window.Blob([file], { type: "plain/text" });
    body.append("file", file);
    return () =>
        fetchApi(`/flows/${flow.id}/${type}/content.data`, {
            method: "POST",
            body,
        });
}

export function clear() {
    return () => fetchApi("/clear", { method: "POST" });
}

export function upload(file) {
    const body = new FormData();
    body.append("file", file);
    return () => fetchApi("/flows/dump", { method: "POST", body });
}

/** Toggle selection for one particular flow. */
export function selectToggle(flow: Flow) {
    return (dispatch: AppDispatch, getState: () => RootState) => {
        const { flows } = getState();
        if (flow.id in flows.selectedIndex) {
            dispatch(select(flows.selected.filter((f) => flow.id !== f.id)));
        } else {
            dispatch(select([...flows.selected, flow]));
        }
    };
}

/** Select a range of flows with shift + click. */
export function selectRange(flow: Flow) {
    return (dispatch: AppDispatch, getState: () => RootState) => {
        const { flows } = getState();
        const prev = flows.selected[flows.selected.length - 1];

        const thisIndex = flows.viewIndex[flow.id];
        const prevIndex = flows.viewIndex[prev?.id];
        if (thisIndex === undefined || prevIndex === undefined) {
            return dispatch(select([flow]));
        }
        let newSelection: Flow[];
        if (thisIndex <= prevIndex) {
            newSelection = flows.view.slice(thisIndex, prevIndex + 1);
        } else {
            newSelection = flows.view.slice(prevIndex + 1, thisIndex + 1);
            newSelection.push(prev); // Keep this at the end if the user shift-clicks again.
        }
        return dispatch(select(newSelection));
    };
}

export default flowsSlice.reducer;
