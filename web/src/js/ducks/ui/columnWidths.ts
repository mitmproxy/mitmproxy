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

// The sized columns fill the table between them, and the filler column takes whatever they leave over.
// Hiding one would widen that instead of the columns that stay, and showing one would push the table past its right edge.
// A column therefore takes its width out of the columns it joins, or hands it back to them, each in proportion to its own width.
export const shareColumnWidths =
    (prevVisible: string[], nextVisible: string[]): AppThunk =>
    (dispatch, getState) => {
        const widths = getState().ui.columnWidths;
        const stay = nextVisible.filter((col) => prevVisible.includes(col));
        const shown = nextVisible.filter((col) => !prevVisible.includes(col));
        const hidden = prevVisible.filter((col) => !nextVisible.includes(col));

        // A column that was never resized has no width of its own: the table stretches it to whatever is left, so it settles the difference already.
        if (prevVisible.concat(nextVisible).some((col) => !widths[col])) return;

        const width = (total: number, col: string) => total + widths[col];
        const total = stay.reduce(width, 0);
        const shared = hidden.reduce(width, 0) - shown.reduce(width, 0);
        if (total + shared <= 0) return;

        dispatch(
            commitColumnWidths(
                Object.fromEntries(
                    stay.map((col) => [
                        col,
                        Math.round((widths[col] * (total + shared)) / total),
                    ]),
                ),
            ),
        );
    };

export const resetColumnWidths = (): AppThunk => (dispatch) => {
    dispatch(clearColumnWidths());
    saveColumnWidths({});
};
