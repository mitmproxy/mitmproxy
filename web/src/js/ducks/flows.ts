import {assertNever, fetchApi} from "../utils";

import { Flow } from "../flow";
import {
    canReplay,
    canResumeOrKill,
    canRevert,
    sortFunctions,
} from "../flow/utils";
import { AppDispatch, RootState } from "./store";
import { FilterName} from "./ui/filter";
import {
    Comparer,
    createAction,
    createSlice,
    PayloadAction,
} from "@reduxjs/toolkit";

export const FLOWS_ADD = createAction<{
    flow: Flow;
    matching_filters: Partial<{ [key in FilterName]: boolean }>;
}>("FLOWS_ADD");
export const FLOWS_UPDATE = createAction<{
    flow: Flow;
    matching_filters: Partial<{ [key in FilterName]: boolean }>;
}>("FLOWS_UPDATE");
export const FLOWS_REMOVE = createAction<string>("FLOWS_REMOVE");
export const FLOWS_RECEIVE = createAction<Flow[]>("FLOWS_RECEIVE");
export const FLOWS_FILTER_UPDATE = createAction<{
    name: FilterName;
    matching_flow_ids: string[];
}>("FLOWS_FILTER_UPDATE");

type FlowSortFn = Comparer<Flow>

export interface FlowsState {
    list: Flow[];
    _listIndex: Map<string, number>;
    byId: Map<string, Flow>;
    view: Flow[];
    _viewIndex: Map<string, number>;

    sort: { column?: keyof typeof sortFunctions; desc: boolean };
    selected: Flow[];
    selectedIds: Set<string>;
    highlighted: Set<string>;
}

export const defaultState: FlowsState = {
    list: [],
    _listIndex: new Map(),
    byId: new Map(),
    view: [],
    _viewIndex: new Map(),

    sort: { column: undefined, desc: false },
    selected: [],
    selectedIds: new Set(),
    highlighted: new Set(),
};

function buildIndex(flows: Flow[]): Map<string, number> {
    return new Map(flows.map((f, i) => [f.id, i]));
}

/// Find the insertion position in a sorted array.
function findInsertPos<T>(list: T[], item: T, sort: Comparer<T>): number {
    let low = 0,
        high = list.length;

    while (low < high) {
        const middle = (low + high) >>> 1;
        if (sort(item, list[middle]) >= 0) {
            low = middle + 1;
        } else {
            high = middle;
        }
    }

    return low;
}

function insertIntoView(state: FlowsState, flow: Flow) {
    const sort = makeSort(state.sort);
    const insert_at_end = (
        state.view.length === 0 ||
        sort(state.view[state.view.length - 1], flow) <= 0
    );
    if(insert_at_end) {
        state.view.push(flow);
        state._viewIndex.set(flow.id, state.view.length - 1);
    } else {
        const insertIdx = findInsertPos(state.view, flow, sort)
        state.view.splice(insertIdx, 0, flow);
        state._viewIndex = buildIndex(state.view);
    }
}

function removeFromView(state: FlowsState, flow_id: string, oldIndex: number) {
    state.view.splice(oldIndex, 1);
    if(oldIndex === state.view.length - 1) {
        state._viewIndex.delete(flow_id);
    } else {
        state._viewIndex = buildIndex(state.view);
    }
}

function updateInView(state: FlowsState, flow: Flow, oldIndex: number) {
    const sort = makeSort(state.sort);
    state.view[oldIndex] = flow;
    const already_sorted = (
        (oldIndex === 0 || sort(state.view[oldIndex - 1], flow) <= 0)
        &&
        (oldIndex === state.view.length - 1 || sort(flow, state.view[oldIndex + 1]) <= 0)
    );
    if(!already_sorted) {
        state.view.sort(sort);
        state._viewIndex = buildIndex(state.view);
    }
}

const flowsSlice = createSlice({
    name: "flows",
    initialState: defaultState,
    reducers: {
        setSort: (
            state,
            action: PayloadAction<{
                column?: keyof typeof sortFunctions;
                desc: boolean;
            }>,
        ) => {
            const sortFn = makeSort(action.payload);
            state.sort = action.payload;
            state.view.sort(sortFn);
            state._viewIndex = buildIndex(state.view);
        },
        select: (state, action: PayloadAction<Flow[]>) => {
            state.selected = action.payload;
            state.selectedIds = new Set(action.payload.map(f => f.id));
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(FLOWS_RECEIVE, (state, action) => {
                const list = action.payload;
                state.list = list;
                state._listIndex = buildIndex(list);

                const byId: Map<string, Flow> = new Map(list.map(f => [f.id, f]));
                state.byId = byId;

                // No filter information yet, we expect that to come immediately after.
                const sorted = list.toSorted(makeSort(state.sort));
                state.view = sorted;
                state._viewIndex = buildIndex(sorted);

                state.selected = state.selectedIds
                    .values()
                    .map(id => byId.get(id))
                    .filter(f => f !== undefined)
                    .toArray();
                state.selectedIds = new Set(state.selected.map(f => f.id));


            })
            .addCase(FLOWS_ADD, (state, action) => {
                const { flow, matching_filters } = action.payload;
                state._listIndex.set(flow.id, state.list.length);
                state.list.push(flow);
                state.byId.set(flow.id, flow);
                if(matching_filters[FilterName.Search] !== false) {
                    insertIntoView(state, flow);
                }
                if(matching_filters[FilterName.Highlight] === true) {
                    state.highlighted.add(flow.id);
                }
            })
            .addCase(FLOWS_UPDATE, (state, action) => {
                const { flow, matching_filters } = action.payload;

                const listIndex = state._listIndex.get(flow.id)!;
                state.list[listIndex] = flow;
                state.byId.set(flow.id, flow);

                const oldIndex = state._viewIndex.get(flow.id);
                const hasOldFlow = oldIndex !== undefined;
                const hasNewFlow = !(matching_filters[FilterName.Search] === false);
                if (hasNewFlow && !hasOldFlow) {
                    insertIntoView(state, flow);
                } else if (!hasNewFlow && hasOldFlow) {
                    removeFromView(state, flow.id, oldIndex)
                } else if (hasNewFlow && hasOldFlow) {
                    updateInView(state, flow, oldIndex);
                }

                if(state.selectedIds.has(flow.id)) {
                    state.selected = state.selected
                        .map(existing => existing.id === flow.id ? flow : existing);
                }

                if(matching_filters[FilterName.Highlight] === true) {
                    state.highlighted.add(flow.id);
                } else {
                    state.highlighted.delete(flow.id);
                }
            })
            .addCase(FLOWS_FILTER_UPDATE, (state, action) => {
                const { name, matching_flow_ids } = action.payload;

                switch(name) {
                    case FilterName.Search: {
                        const view = matching_flow_ids
                            .map(id => state.byId.get(id))
                            .filter(f => f !== undefined);
                        view.sort(makeSort(state.sort));
                        state.view = view;
                        state._viewIndex = buildIndex(view);
                        break;
                    }
                    case FilterName.Highlight:
                        state.highlighted = new Set(matching_flow_ids);
                        break;
                    /* istanbul ignore next @preserve */
                    default:
                        assertNever(name);
                }
            })
            .addCase(FLOWS_REMOVE, (state, action) => {
                const flow_id = action.payload;
                state.list.splice(state._listIndex.get(flow_id)!, 1);
                state._listIndex.delete(flow_id);
                state.byId.delete(flow_id);
                const viewIndex = state._viewIndex.get(flow_id);
                if(viewIndex !== undefined) {
                    removeFromView(state, flow_id, viewIndex);
                }

                if(state.selectedIds.delete(flow_id)) {
                    if(state.selectedIds.size === 0 && viewIndex !== undefined) {
                        const fallback =
                            state.view[viewIndex /* no +1, already removed */] ??
                            state.view[viewIndex - 1];
                        state.selected = [fallback];
                        state.selectedIds.add(fallback.id);
                    } else {
                        state.selected = state.selected.filter(f => f.id !== flow_id);
                    }
                }

                state.highlighted.delete(flow_id);
            })

    },
});


export const { setSort, select } = flowsSlice.actions;


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
        flows._viewIndex.get(flows.selected[flows.selected.length - 1]?.id);
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
        if (flows.selectedIds.has(flow.id)) {
            dispatch(select(flows.selected.filter(f => f !== flow)));
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

        const thisIndex = flows._viewIndex.get(flow.id);
        const prevIndex = flows._viewIndex.get(prev?.id);
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
