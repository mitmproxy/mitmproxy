import { fetchApi } from "../utils";

import * as store from "./utils/store";
import Filt from "../filt/filt";
import { Flow } from "../flow";
import {canResumeOrKill, canRevert, sortFunctions} from "../flow/utils";
import {AppDispatch, RootState} from "./store";

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
    selected: string[];
}

export const defaultState: FlowsState = {
    highlight: undefined,
    filter: undefined,
    sort: { column: undefined, desc: false },
    selected: [],
    ...store.defaultState,
};

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

            let selected = state.selected;
            if (
                action.type === REMOVE &&
                state.selected.includes(action.data)
            ) {
                if (state.selected.length > 1) {
                    selected = []; // clear selection when multiple flows are selected and removed, no `nextSelection` logic in this case
                } else {
                    selected = [];
                    if (
                        action.data in state.viewIndex &&
                        state.view.length > 1
                    ) {
                        const currentIndex = state.viewIndex[action.data];
                        let nextSelection;
                        if (currentIndex === state.view.length - 1) {
                            // last row
                            nextSelection = state.view[currentIndex - 1];
                        } else {
                            nextSelection = state.view[currentIndex + 1];
                        }
                        selected.push(nextSelection.id);
                    }
                }
            }

            return {
                ...state,
                selected,
                ...store.reduce(state, storeAction),
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

        case SELECT:
            return {
                ...state,
                selected: action.flowIds,
            };

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

export function selectRelative(flows, shift: number) {
    const currentSelectionIndex = flows.viewIndex[flows.selected[flows.selected.length - 1]];
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
    return select(flow ? [flow.id] : []);
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

export function select(flowIds: string[]) {
    return {
        type: SELECT,
        flowIds: flowIds,
    };
}

/** Toggle selection for one particular flow. */
export function toggleSelect(flowId: string) {
    return (dispatch: AppDispatch, getState: () => RootState) => {
        const flowIds = getState().flows.selected;
        if (flowIds.includes(flowId)) {
            dispatch(select(flowIds.filter(id => id !== flowId)));
        } else {
            dispatch(select([...flowIds, flowId]));
        }
    }
}
