import { fetchApi } from "../utils";

import * as store from "./utils/store";
import Filt from "../filt/filt";
import { Flow } from "../flow";
import {canResumeOrKill, canRevert, sortFunctions} from "../flow/utils";
import {AppDispatch, RootState} from "./store";
import {State} from "./utils/store";

export const ADD = "FLOWS_ADD";
export const UPDATE = "FLOWS_UPDATE";
export const REMOVE = "FLOWS_REMOVE";
export const RECEIVE = "FLOWS_RECEIVE";
export const SELECT = "FLOWS_SELECT";
export const SET_FILTER = "FLOWS_SET_FILTER";
export const SET_SORT = "FLOWS_SET_SORT";
export const SET_HIGHLIGHT = "FLOWS_SET_HIGHLIGHT";

interface FlowSortFn extends store.SortFn<Flow> {}

interface FlowFilterFn extends store.FilterFn<Flow> {}

export interface FlowsState extends store.State<Flow> {
    highlight?: string;
    filter?: string;
    sort: { column?: keyof typeof sortFunctions; desc: boolean };
    selected: Flow[];
    selectedIndex: {[id: string]: number};
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
    action,
): Pick<FlowsState, "selected" | "selectedIndex"> {
    let {selected, selectedIndex} = state;
    switch (action.type) {
        case UPDATE:
            if(selectedIndex[action.data.id] === undefined) {
                break;
            }
            selected = selected.map(f => f.id === action.data.id ? action.data : f);
            break;
        case RECEIVE:
            selected = selected.map(f => newStoreState.byId[f.id]).filter(f => f !== undefined);
            selectedIndex = Object.fromEntries(selected.map(((f, i) => [f.id, i])));
            break;
        case REMOVE:
            if(selectedIndex[action.data] === undefined) {
                break;
            }
            if (selected.length > 1) {
                selected = selected.filter(f => f.id !== action.data);
            } else if (!(action.data in state.viewIndex)) {
                selected = [];
            } else {
                const currentIndex = state.viewIndex[action.data];
                selected = [
                    state.view[currentIndex + 1]
                    ?? state.view[currentIndex - 1]  // last element
                ];
            }
            selectedIndex = Object.fromEntries(selected.map(((f, i) => [f.id, i])));
            break;
    }
    return {selected, selectedIndex};
}

export default function reducer(
    state: FlowsState = defaultState,
    action,
): FlowsState {
    switch (action.type) {
        case ADD:
        case UPDATE:
        case REMOVE:
        case RECEIVE: {
            const storeAction = store[action.cmd](
                action.data,
                makeFilter(state.filter),
                makeSort(state.sort),
            );
            const newStoreState = store.reduce(state, storeAction);
            return {
                ...state,
                ...newStoreState,
                ...updateSelected(state, newStoreState, action),
            };
        }
        case SET_FILTER:
            return {
                ...state,
                filter: action.filter,
                ...store.reduce(
                    state,
                    store.setFilter(
                        makeFilter(action.filter),
                        makeSort(state.sort),
                    ),
                ),
            };

        case SET_HIGHLIGHT:
            return {
                ...state,
                highlight: action.highlight,
            };

        case SET_SORT:
            return {
                ...state,
                sort: action.sort,
                ...store.reduce(state, store.setSort(makeSort(action.sort))),
            };

        case SELECT: {
            const selected: Flow[] = action.flows;
            return {
                ...state,
                selected,
                selectedIndex: Object.fromEntries(selected.map(((f, i) => [f.id, i]))),
            };
        }
        default:
            return state;
    }
}

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

export function setFilter(filter: string) {
    return { type: SET_FILTER, filter };
}

export function setHighlight(highlight: string) {
    return { type: SET_HIGHLIGHT, highlight };
}

export function setSort(column: string, desc: boolean) {
    return { type: SET_SORT, sort: { column, desc } };
}

export function selectRelative(flows: FlowsState, shift: number) {
    const currentSelectionIndex: number | undefined = flows.viewIndex[flows.selected[flows.selected.length - 1]?.id];
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
            flows.map(flow =>
                fetchApi(`/flows/${flow.id}/duplicate`, { method: "POST" }),
            ),
        );
}

export function replay(flow: Flow) {
    return () => fetchApi(`/flows/${flow.id}/replay`, { method: "POST" });
}

export function revert(flows: Flow[]) {
    flows = flows.filter(canRevert);
    return () =>
        Promise.all(
            flows.map(flow =>
                fetchApi(`/flows/${flow.id}/revert`, { method: "POST" }),
            ),
        );
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

export function select(flows: Flow[]) {
    return {
        type: SELECT,
        flows,
    };
}

/** Toggle selection for one particular flow. */
export function selectToggle(flow: Flow) {
    return (dispatch: AppDispatch, getState: () => RootState) => {
        const {flows} = getState();
        if (flow.id in flows.selectedIndex) {
            dispatch(select(flows.selected.filter(f => flow.id !== f.id)));
        } else {
            dispatch(select([...flows.selected, flow]));
        }
    }
}

/** Select a range of flows with shift + click. */
export function selectRange(flow: Flow) {
    return (dispatch: AppDispatch, getState: () => RootState) => {
        const {flows} = getState();
        const prev = flows.selected[flows.selected.length - 1];

        const thisIndex = flows.viewIndex[flow.id];
        const prevIndex = flows.viewIndex[prev?.id];
        if(thisIndex === undefined || prevIndex === undefined) {
            return dispatch(select([flow]));
        }
        let newSelection: Flow[];
        if(thisIndex <= prevIndex) {
            newSelection = flows.view.slice(thisIndex, prevIndex + 1);
        } else {
            newSelection = flows.view.slice(prevIndex + 1, thisIndex + 1);
            newSelection.push(prev);  // Keep this at the end if the user shift-clicks again.
        }
        return dispatch(select(newSelection));
    }
}
