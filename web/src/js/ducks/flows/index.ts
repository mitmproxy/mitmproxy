import { assertNever } from "../../utils";

import { Flow } from "../../flow";
import { sortFunctions } from "../../flow/utils";
import { AppDispatch, RootState } from "../store";
import { FilterName } from "../ui/filter";
import { Comparer, createAction, UnknownAction } from "@reduxjs/toolkit";
import {
    buildIndex,
    buildLookup,
    insertViewItem,
    removeViewItemAt,
    updateViewItem,
    withElemRemoved,
} from "./_utils";
import { toSorted, toSpliced } from "./_compat";

export * from "./_backend_actions";

export const FLOWS_ADD = createAction<{
    flow: Flow;
    matching_filters: Partial<{ [key in FilterName]: boolean }>;
}>("flows/add");
export const FLOWS_UPDATE = createAction<{
    flow: Flow;
    matching_filters: Partial<{ [key in FilterName]: boolean }>;
}>("flows/update");
export const FLOWS_REMOVE = createAction<string>("flows/remove");
export const FLOWS_RECEIVE = createAction<Flow[]>("flows/receive");
export const FLOWS_FILTER_UPDATE = createAction<{
    name: FilterName;
    matching_flow_ids: string[] | null;
}>("flows/filterUpdate");

export const setSort = createAction<{
    column?: keyof typeof sortFunctions;
    desc: boolean;
}>("flows/sort");
export const select = createAction<Flow[]>("flows/select");

export interface FlowsState {
    list: Flow[];
    _listIndex: Map<string, number>;
    byId: Map<string, Flow>;
    view: Flow[];
    _viewIndex: Map<string, number>;

    sort: { column?: keyof typeof sortFunctions; desc: boolean };
    selected: Flow[];
    selectedIds: Set<string>;
    highlightedIds: Set<string>;
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
    highlightedIds: new Set(),
};

// This is a manual reducer as RTK's createSlice always uses Immer, which is orders of magnitude slower.
//
// **WebSocket/HTTP race:**
// After establishing a WebSocket connection with the backend, mitmweb will fetch the flow list over HTTP.
// They are not sent over WebSocket for performance reasons. While flows are being fetched we buffer all events.
// This is racy: We may see flows/add events for flows that are already in the view, or update/remove events
// for flows that aren't known at all. The reducer needs to handle these cases gracefully.
export default function flowsReducer(
    state = defaultState,
    action: UnknownAction,
): FlowsState {
    if (FLOWS_RECEIVE.match(action)) {
        const { sort } = state;
        const list = action.payload;
        const _listIndex = buildIndex(list);
        const byId = new Map(list.map((f) => [f.id, f]));
        // No filter information yet, we expect that to come immediately after.
        const view = toSorted(list, makeSort(sort));
        const _viewIndex = buildIndex(view);
        const selected = state.selected
            .map((flow) => byId.get(flow.id))
            .filter((f) => f !== undefined);
        const selectedIds = buildLookup(selected);
        const highlightedIds = new Set<string>();

        return {
            list,
            _listIndex,
            byId,
            view,
            _viewIndex,
            sort,
            selected,
            selectedIds,
            highlightedIds,
        };
    } else if (FLOWS_ADD.match(action)) {
        const { flow, matching_filters } = action.payload;
        if (state._listIndex.has(flow.id)) {
            return state; // WebSocket/HTTP race
        }
        const { sort, selected, selectedIds } = state;
        let { view, _viewIndex, highlightedIds } = state;
        // Update list
        const _listIndex = new Map(state._listIndex);
        _listIndex.set(flow.id, state.list.length);
        const list = [...state.list, flow];
        const byId = new Map(state.byId);
        byId.set(flow.id, flow);
        // Update view if filter matches (true) or is unset (undefined).
        if (
            matching_filters[FilterName.Search] === true ||
            matching_filters[FilterName.Search] === undefined
        ) {
            ({ view, _viewIndex } = insertViewItem(
                view,
                _viewIndex,
                flow,
                makeSort(sort),
            ));
        }
        // Update highlight
        if (matching_filters[FilterName.Highlight] === true) {
            highlightedIds = new Set(highlightedIds);
            highlightedIds.add(flow.id);
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
            highlightedIds,
        };
    } else if (FLOWS_UPDATE.match(action)) {
        const { flow, matching_filters } = action.payload;
        const { _listIndex, sort, selectedIds } = state;
        let { view, _viewIndex, selected, highlightedIds } = state;
        // Update list
        const listPos = state._listIndex.get(flow.id);
        const list = [...state.list];
        if (listPos !== undefined) {
            list[listPos] = flow;
        } else {
            // WebSocket/HTTP race. We could theoretically swallow this (expecting a flows/remove event still queued),
            // but performance is not important here and adding the flow may generally be a bit more robust.
            list.push(flow);
        }
        const byId = new Map(state.byId);
        byId.set(flow.id, flow);
        // Update view
        const prevViewPos: number | undefined = _viewIndex.get(flow.id);
        const hasOldFlow = prevViewPos !== undefined;
        const hasNewFlow =
            matching_filters[FilterName.Search] === true ||
            matching_filters[FilterName.Search] === undefined;
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
                prevViewPos,
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
        if (selectedIds.has(flow.id)) {
            selected = selected.map((existing) =>
                existing.id === flow.id ? flow : existing,
            );
        }
        // Update highlight
        if (matching_filters[FilterName.Highlight] === true) {
            if (!highlightedIds.has(flow.id)) {
                highlightedIds = new Set(highlightedIds);
                highlightedIds.add(flow.id);
            }
        } else {
            highlightedIds = withElemRemoved(highlightedIds, flow.id);
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
            highlightedIds,
        };
    } else if (FLOWS_REMOVE.match(action)) {
        const flow_id = action.payload;
        const { sort } = state;
        let { view, _viewIndex, selected, selectedIds } = state;
        const listPos = state._listIndex.get(flow_id);
        if (listPos === undefined) {
            return state; // WebSocket/HTTP race
        }
        const list = toSpliced(state.list, listPos, 1);
        const _listIndex = buildIndex(list);
        const byId = new Map(state.byId);
        byId.delete(flow_id);
        // Update view
        const viewPos = _viewIndex.get(flow_id);
        if (viewPos !== undefined) {
            ({ view, _viewIndex } = removeViewItemAt(
                view,
                _viewIndex,
                viewPos,
            ));
        }
        // Update selection
        if (selectedIds.has(flow_id)) {
            if (selected.length === 1 && viewPos !== undefined) {
                const fallback =
                    view[viewPos /* no +1, already removed */] ??
                    view[viewPos - 1];
                selected = fallback ? [fallback] : [];
            } else {
                selected = selected.filter((f) => f.id !== flow_id);
            }
            selectedIds = buildLookup(selected);
        }
        // Update highlight
        const highlightedIds = withElemRemoved(state.highlightedIds, flow_id);

        return {
            list,
            _listIndex,
            byId,
            view,
            _viewIndex,
            sort,
            selected,
            selectedIds,
            highlightedIds,
        };
    } else if (FLOWS_FILTER_UPDATE.match(action)) {
        const { name, matching_flow_ids } = action.payload;
        switch (name) {
            case FilterName.Search: {
                const view = toSorted(
                    matching_flow_ids === null
                        ? state.list
                        : matching_flow_ids
                              .map((id) => state.byId.get(id))
                              // WebSocket/HTTP race
                              .filter((f) => f !== undefined),
                    makeSort(state.sort),
                );
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
                    highlightedIds: new Set(matching_flow_ids),
                };
            /* istanbul ignore next @preserve */
            default:
                assertNever(name);
        }
    } else if (setSort.match(action)) {
        const sort = action.payload;
        let view: Flow[];
        if (sort.column) {
            view = toSorted(state.view, makeSort(sort));
        } else {
            // Restore original order if column isn't specified.
            view = state.list.filter((f) => state._viewIndex.has(f.id));
        }
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
    const currentSelectionIndex: number | undefined = flows._viewIndex.get(
        lastSelected?.id,
    );
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

/** Toggle selection for one particular flow. */
export function selectToggle(flow: Flow) {
    return (dispatch: AppDispatch, getState: () => RootState) => {
        const { flows } = getState();
        if (flows.selectedIds.has(flow.id)) {
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
