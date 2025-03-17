import { fetchApi } from "../utils";

import * as store from "./utils/store";
import { Flow } from "../flow";
import { sortFunctions } from "../flow/utils";

export const ADD = "FLOWS_ADD";
export const UPDATE = "FLOWS_UPDATE";
export const REMOVE = "FLOWS_REMOVE";
export const RECEIVE = "FLOWS_RECEIVE";
export const SELECT = "FLOWS_SELECT";
export const SET_FILTER = "FLOWS_SET_FILTER";
export const SET_SORT = "FLOWS_SET_SORT";
export const SET_HIGHLIGHT = "FLOWS_SET_HIGHLIGHT";

export const SERVER_UPDATE = "FLOWS_SERVER_UPDATE";
export const FILTERS_UPDATED = "FLOWS_FILTERSUPDATED";

interface FlowSortFn extends store.SortFn<Flow> {}

interface FlowFilterFn extends store.FilterFn<Flow> {}

export interface FlowsState extends store.State<Flow> {
    highlight?: string;
    filter?: string;
    matchedIds?: string[];
    sort: { column?: keyof typeof sortFunctions; desc: boolean };
    selected: string[];
}

export const defaultState: FlowsState = {
    highlight: undefined,
    filter: undefined,
    sort: { column: undefined, desc: false },
    selected: [],
    matchedIds: undefined,
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
                makeFilter(state.matchedIds),
                makeSort(state.sort),
            );

            let selected = state.selected;
            if (
                action.type === REMOVE &&
                state.selected.includes(action.data)
            ) {
                if (state.selected.length > 1) {
                    selected = selected.filter((x) => x !== action.data);
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
            };

        case FILTERS_UPDATED: {
            console.log("FILTERS_UPDATED");
            const matchedIds = action.expr !== "" ? action.data : undefined;
            return {
                ...state,
                filter: action.expr,
                matchedIds: matchedIds,
                ...store.reduce(
                    state,
                    store.setFilter<Flow>(
                        makeFilter(matchedIds),
                        makeSort(state.sort),
                    ),
                ),
            };
        }

        case SERVER_UPDATE: {
            const flow: Flow = action.data;
            const matches: Record<string, boolean> = action.matches;
            const currentFilter = state.filter;

            const newMatchedIds = state.matchedIds ? [...state.matchedIds] : [];

            if (
                Object.keys(matches).length === 0 ||
                (currentFilter && matches[currentFilter])
            ) {
                if (!newMatchedIds.includes(flow.id)) {
                    newMatchedIds.push(flow.id);
                }
            } else {
                const index = newMatchedIds.indexOf(flow.id);
                if (index > -1) {
                    newMatchedIds.splice(index, 1);
                }
            }

            const isKnown = flow.id in state.byId;
            const cmd = isKnown ? store.update : store.add;

            const storeAction = cmd<Flow>(
                flow,
                makeFilter(newMatchedIds),
                makeSort(state.sort),
            );

            return {
                ...state,
                matchedIds: newMatchedIds,
                ...store.reduce(state, storeAction),
            };
        }

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

export function makeFilter(matchedIds?: string[]): FlowFilterFn | undefined {
    if (!matchedIds) {
        return;
    }
    const idSet = new Set(matchedIds);
    return (flow) => idSet.has(flow.id);
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

export function serverFlowUpdate(flow: Flow, matches: Record<string, boolean>) {
    return {
        type: SERVER_UPDATE,
        data: flow,
        matches,
    };
}

export function setFilter(filter: string) {
    if (window.backend) {
        window.backend.updateFilter("search", filter);
    }
    return { type: SET_FILTER, filter };
}

export function setHighlight(highlight: string) {
    if (window.backend) {
        window.backend.updateFilter("highlight", highlight);
    }
    return { type: SET_HIGHLIGHT, highlight };
}

export function setSort(column: string, desc: boolean) {
    return { type: SET_SORT, sort: { column, desc } };
}

export function selectRelative(flows, shift) {
    const currentSelectionIndex = flows.viewIndex[flows.selected[0]];
    const minIndex = 0;
    const maxIndex = flows.view.length - 1;
    let newIndex;
    if (currentSelectionIndex === undefined) {
        newIndex = shift < 0 ? minIndex : maxIndex;
    } else {
        newIndex = currentSelectionIndex + shift;
        newIndex = window.Math.max(newIndex, minIndex);
        newIndex = window.Math.min(newIndex, maxIndex);
    }
    const flow = flows.view[newIndex];
    return select(flow ? flow.id : undefined);
}

export function resume(flow: Flow) {
    return () => fetchApi(`/flows/${flow.id}/resume`, { method: "POST" });
}

export function resumeAll() {
    return () => fetchApi("/flows/resume", { method: "POST" });
}

export function kill(flow: Flow) {
    return () => fetchApi(`/flows/${flow.id}/kill`, { method: "POST" });
}

export function killAll() {
    return () => fetchApi("/flows/kill", { method: "POST" });
}

export function remove(flow: Flow) {
    return () => fetchApi(`/flows/${flow.id}`, { method: "DELETE" });
}

export function duplicate(flow: Flow) {
    return () => fetchApi(`/flows/${flow.id}/duplicate`, { method: "POST" });
}

export function replay(flow: Flow) {
    return () => fetchApi(`/flows/${flow.id}/replay`, { method: "POST" });
}

export function revert(flow: Flow) {
    return () => fetchApi(`/flows/${flow.id}/revert`, { method: "POST" });
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

export function select(id?: string) {
    return {
        type: SELECT,
        flowIds: id ? [id] : [],
    };
}
