import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { AppThunk } from "../store";

export type ColumnWidths = Record<string, number>;

const STORAGE_KEY = "mitmweb-column-widths";

// Storage may be unavailable, and whatever is in it was written by a version we know nothing about.
export function loadColumnWidths(): ColumnWidths {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function saveColumnWidths(widths: ColumnWidths) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(widths));
    } catch {
        /* persistence is best-effort */
    }
}

const columnWidthsSlice = createSlice({
    name: "ui/columnWidths",
    initialState: loadColumnWidths(),
    reducers: {
        setColumnWidths(state, action: PayloadAction<ColumnWidths>) {
            return { ...state, ...action.payload };
        },
        clearColumnWidths() {
            return {};
        },
    },
});

const { actions, reducer } = columnWidthsSlice;
export const { setColumnWidths, clearColumnWidths } = actions;
export default reducer;

// A drag reports a width every frame, so only the one it settles on is worth writing out.
export const commitColumnWidths =
    (widths: ColumnWidths): AppThunk =>
    (dispatch, getState) => {
        dispatch(setColumnWidths(widths));
        saveColumnWidths(getState().ui.columnWidths);
    };

export const resetColumnWidths = (): AppThunk => (dispatch) => {
    dispatch(clearColumnWidths());
    saveColumnWidths({});
};
