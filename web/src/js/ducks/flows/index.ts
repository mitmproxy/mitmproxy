import { assertNever, fetchApi } from "../../utils";

import { Flow } from "../../flow";
import {
    canReplay,
    canResumeOrKill,
    canRevert,
    sortFunctions,
} from "../../flow/utils";
import { AppDispatch, RootState } from "../store";
import { FilterName } from "../ui/filter";
import { Comparer, createAction, UnknownAction } from "@reduxjs/toolkit";
import {
    buildIndex,
    buildLookup,
    insertViewItem,
    removeViewItemAt,
    updateViewItem,
    withKeyRemoved,
} from "./utils";

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

export const setSort = createAction<{
    column?: keyof typeof sortFunctions;
    desc: boolean;
}>("flows/sort");
export const select = createAction<Flow[]>("flows/select");

export interface FlowsState {
    list: Flow[];
    _listIndex: { [id: string]: number };
    byId: { [id: string]: Flow };
    view: Flow[];
    _viewIndex: { [id: string]: number };

    sort: { column?: keyof typeof sortFunctions; desc: boolean };
    selected: Flow[];
    selectedIds: { [id: string]: boolean };
    highlighted: { [id: string]: boolean };
}

export const defaultState: FlowsState = {
    list: [],
    _listIndex: {},
    byId: {},
    view: [],
    _viewIndex: {},

    sort: { column: undefined, desc: false },
    selected: [],
    selectedIds: {},
    highlighted: {},
};

// This is a manual reducer as RTK's createSlice always uses Immer, which is orders of magnitude slower.
// In benchmarking we found no major difference between Map/Set and objects, so we use objects
// for redux compatibility.
export default function flowsReducer(
    state = defaultState,
    action: UnknownAction,
): FlowsState {
    if (FLOWS_RECEIVE.match(action)) {
        const { sort } = state;
        const list = action.payload;
        const _listIndex = buildIndex(list);
        const byId = Object.fromEntries(list.map((f) => [f.id, f]));
        // No filter information yet, we expect that to come immediately after.
        const view = list.toSorted(makeSort(sort));
        const _viewIndex = buildIndex(view);
        const selected = Object.keys(state.selectedIds)
            .map((id) => byId[id])
            .filter((f) => f !== undefined);
        const selectedIds = buildLookup(state.selected);
        const highlighted = {};

        return {
            list,
            _listIndex,
            byId,
            view,
            _viewIndex,
            sort,
            selected,
            selectedIds,
            highlighted,
        };
    } else if (FLOWS_ADD.match(action)) {
        const { flow, matching_filters } = action.payload;
        const { sort, selected, selectedIds } = state;
        let { view, _viewIndex, highlighted } = state;
        // Update list
        const _listIndex = {
            ...state._listIndex,
            [flow.id]: state.list.length,
        };
        const list = [...state.list, flow];
        const byId = { ...state.byId, [flow.id]: flow };
        // Update view
        if (matching_filters[FilterName.Search] !== false) {
            ({ view, _viewIndex } = insertViewItem(
                view,
                _viewIndex,
                flow,
                makeSort(sort),
            ));
        }
        // Update highlight
        if (matching_filters[FilterName.Highlight] === true) {
            highlighted = { ...highlighted, [flow.id]: true };
        }

        return {
            list,
            _listIndex,
            byId,
            view,
            _viewIndex,
            sort,
            selected,
            selectedIds,
            highlighted,
        };
    } else if (FLOWS_UPDATE.match(action)) {
        const { flow, matching_filters } = action.payload;
        const { _listIndex, sort, selectedIds } = state;
        let { view, _viewIndex, selected, highlighted } = state;
        // Update list
        const listPos = state._listIndex[flow.id];
        const list = [...state.list];
        list[listPos] = flow;
        const byId = { ...state.byId, [flow.id]: flow };
        // Update view
        const prevPos = _viewIndex[flow.id];
        const hasOldFlow = prevPos !== undefined;
        const hasNewFlow = !(matching_filters[FilterName.Search] === false);
        if (hasNewFlow && !hasOldFlow) {
            ({ view, _viewIndex } = insertViewItem(
                view,
                _viewIndex,
                flow,
                makeSort(sort),
            ));
        } else if (!hasNewFlow && hasOldFlow) {
            ({ view, _viewIndex } = removeViewItemAt(
                view,
                _viewIndex,
                prevPos,
            ));
        } else if (hasNewFlow && hasOldFlow) {
            ({ view, _viewIndex } = updateViewItem(
                view,
                _viewIndex,
                flow,
                makeSort(sort),
            ));
        }
        // Update selection
        if (flow.id in state.selectedIds) {
            selected = selected.map((existing) =>
                existing.id === flow.id ? flow : existing,
            );
        }
        // Update highlight
        if (matching_filters[FilterName.Highlight]) {
            if (!(flow.id in highlighted)) {
                highlighted = { ...highlighted, [flow.id]: true };
            }
        } else {
            highlighted = withKeyRemoved(highlighted, flow.id);
        }

        return {
            list,
            _listIndex,
            byId,
            view,
            _viewIndex,
            sort,
            selected,
            selectedIds,
            highlighted,
        };
    } else if (FLOWS_REMOVE.match(action)) {
        const flow_id = action.payload;
        const { sort } = state;
        let { view, _viewIndex, selected, selectedIds } = state;
        const listPos = state._listIndex[flow_id];
        const list = state.list.toSpliced(listPos, 1);
        const _listIndex = withKeyRemoved(state._listIndex, flow_id);
        const byId = withKeyRemoved(state.byId, flow_id);
        // Update view
        const viewPos = _viewIndex[flow_id];
        if (viewPos !== undefined) {
            ({ view, _viewIndex } = removeViewItemAt(
                view,
                _viewIndex,
                viewPos,
            ));
        }
        // Update selection
        if (flow_id in selectedIds) {
            if (selected.length === 1 && viewPos !== undefined) {
                const fallback =
                    view[viewPos /* no +1, already removed */] ??
                    view[viewPos - 1];
                selected = [fallback];
            } else {
                selected = selected.filter((f) => f.id !== flow_id);
            }
            selectedIds = buildLookup(selected);
        }
        // Update highlight
        const highlighted = withKeyRemoved(state.highlighted, flow_id);

        return {
            list,
            _listIndex,
            byId,
            view,
            _viewIndex,
            sort,
            selected,
            selectedIds,
            highlighted,
        };
    } else if (FLOWS_FILTER_UPDATE.match(action)) {
        const { name, matching_flow_ids } = action.payload;
        switch (name) {
            case FilterName.Search: {
                const view = matching_flow_ids
                    .map((id) => state.byId[id])
                    .filter((f) => f !== undefined)
                    .toSorted(makeSort(state.sort));
                const _viewIndex = buildIndex(view);
                return {
                    ...state,
                    view,
                    _viewIndex,
                };
            }
            case FilterName.Highlight:
                return {
                    ...state,
                    highlighted: Object.fromEntries(
                        matching_flow_ids.map((id) => [id, true]),
                    ),
                };
            /* istanbul ignore next @preserve */
            default:
                assertNever(name);
        }
    } else if (setSort.match(action)) {
        const sort = action.payload;
        const view = state.view.toSorted(makeSort(sort));
        const _viewIndex = buildIndex(view);
        return {
            ...state,
            sort,
            view,
            _viewIndex,
        };
    } else if (select.match(action)) {
        return {
            ...state,
            selected: action.payload,
            selectedIds: buildLookup(action.payload),
        };
    } else {
        return state;
    }
}

export function makeSort({
    column,
    desc,
}: {
    column?: keyof typeof sortFunctions;
    desc: boolean;
}): Comparer<Flow> {
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
    const lastSelected: Flow | undefined =
        flows.selected[flows.selected.length - 1];
    const currentSelectionIndex: number | undefined =
        flows._viewIndex[lastSelected?.id];
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
        if (flow.id in flows.selectedIds) {
            dispatch(select(flows.selected.filter((f) => f !== flow)));
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

        const thisIndex = flows._viewIndex[flow.id];
        const prevIndex = flows._viewIndex[prev?.id];
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
