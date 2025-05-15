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
    withKeyRemoved,
} from "./utils";

export * from "./_backend_actions";

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
        const byId = new Map(list.map((f) => [f.id, f]));
        // No filter information yet, we expect that to come immediately after.
        const view = list.toSorted(makeSort(sort));
        const _viewIndex = buildIndex(view);
        const selected = state.selected
            .map((flow) => byId.get(flow.id))
            .filter((f) => f !== undefined)
        const selectedIds = buildLookup(selected);
        const highlighted = new Set<string>();

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
        const _listIndex = new Map(state._listIndex);
        _listIndex.set(flow.id, state.list.length);
        const list = [...state.list, flow];
        const byId = new Map(state.byId);
        byId.set(flow.id, flow);
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
            highlighted = new Set(highlighted);
            highlighted.add(flow.id);
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
        const listPos = state._listIndex.get(flow.id)!;
        const list = [...state.list];
        list[listPos] = flow;
        const byId = new Map(state.byId);
        byId.set(flow.id, flow);
        // Update view
        const prevViewPos: number | undefined = _viewIndex.get(flow.id);
        const hasOldFlow = prevViewPos !== undefined;
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
        if (matching_filters[FilterName.Highlight]) {
            if (!highlighted.has(flow.id)) {
                highlighted = new Set(highlighted);
                highlighted.add(flow.id);
            }
        } else {
            highlighted = withElemRemoved(highlighted, flow.id);
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
        const listPos = state._listIndex.get(flow_id)!;
        const list = state.list.toSpliced(listPos, 1);
        const _listIndex = withKeyRemoved(state._listIndex, flow_id);
        const byId = withKeyRemoved(state.byId, flow_id);
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
                selected = [fallback];
            } else {
                selected = selected.filter((f) => f.id !== flow_id);
            }
            selectedIds = buildLookup(selected);
        }
        // Update highlight
        const highlighted = withElemRemoved(state.highlighted, flow_id);

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
                    .map((id) => state.byId.get(id))
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
                    highlighted: new Set(matching_flow_ids),
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
