import reducer, {
    clearColumnWidths,
    commitColumnWidths,
    loadColumnWidths,
    resetColumnWidths,
    setColumnWidths,
    shareColumnWidths,
} from "../../../ducks/ui/columnWidths";
import { TStore } from "../tutils";

const COLUMN_WIDTHS_KEY = "mitmweb-column-widths";

beforeEach(() => localStorage.clear());

describe("column widths reducer", () => {
    it("merges the widths it is given into the ones already pinned", () => {
        const state = reducer({ size: 70 }, setColumnWidths({ time: 45 }));
        expect(reducer(state, setColumnWidths({ size: 90 }))).toEqual({
            size: 90,
            time: 45,
        });
    });

    it("unpins every column when cleared", () => {
        expect(reducer({ size: 70 }, clearColumnWidths())).toEqual({});
    });
});

describe("loadColumnWidths", () => {
    it("reads the persisted widths", () => {
        localStorage.setItem(
            COLUMN_WIDTHS_KEY,
            JSON.stringify({ size: 123, time: 45 }),
        );
        expect(loadColumnWidths()).toEqual({ size: 123, time: 45 });
    });

    it("starts from unsized columns when there is nothing to read", () => {
        expect(loadColumnWidths()).toEqual({});
    });

    it("starts from unsized columns when what is stored cannot be read", () => {
        localStorage.setItem(COLUMN_WIDTHS_KEY, "}{");
        expect(loadColumnWidths()).toEqual({});
    });
});

describe("column widths thunks", () => {
    it("persists the widths a resize settled on", () => {
        const store = TStore();
        store.dispatch(setColumnWidths({ size: 70 }));
        expect(localStorage.getItem(COLUMN_WIDTHS_KEY)).toBeNull();

        store.dispatch(commitColumnWidths({ time: 45 }));

        expect(JSON.parse(localStorage.getItem(COLUMN_WIDTHS_KEY)!)).toEqual({
            size: 70,
            time: 45,
        });
    });

    it("clears the persisted widths on reset", () => {
        const store = TStore();
        store.dispatch(commitColumnWidths({ size: 70 }));

        store.dispatch(resetColumnWidths());

        expect(store.getState().ui.columnWidths).toEqual({});
        expect(JSON.parse(localStorage.getItem(COLUMN_WIDTHS_KEY)!)).toEqual(
            {},
        );
    });

    it("keeps the widths in the store when they cannot be persisted", () => {
        const setItem = jest
            .spyOn(Storage.prototype, "setItem")
            .mockImplementation(() => {
                throw new Error("quota exceeded");
            });
        const store = TStore();

        store.dispatch(commitColumnWidths({ size: 70 }));

        expect(store.getState().ui.columnWidths).toEqual({ size: 70 });
        setItem.mockRestore();
    });
});

describe("shareColumnWidths", () => {
    const sized = () => {
        const store = TStore();
        store.dispatch(
            commitColumnWidths({ method: 60, status: 80, size: 60 }),
        );
        return store;
    };

    it("hands the width of a hidden column to the columns that stay", () => {
        const store = sized();

        store.dispatch(
            shareColumnWidths(["method", "status", "size"], ["method", "size"]),
        );

        expect(store.getState().ui.columnWidths).toEqual({
            method: 100,
            status: 80,
            size: 100,
        });
    });

    it("takes the width a column comes back with out of the others", () => {
        const store = sized();

        store.dispatch(
            shareColumnWidths(["method", "size"], ["method", "status", "size"]),
        );

        expect(store.getState().ui.columnWidths).toEqual({
            method: 20,
            status: 80,
            size: 20,
        });
    });

    it("leaves the widths to the column that is stretched to fit", () => {
        const store = sized();

        store.dispatch(
            shareColumnWidths(["path", "method", "status"], ["path", "method"]),
        );

        expect(store.getState().ui.columnWidths).toEqual({
            method: 60,
            status: 80,
            size: 60,
        });
    });

    it("has nothing to share out until a column is resized", () => {
        const store = TStore();

        store.dispatch(shareColumnWidths(["method", "status"], ["method"]));

        expect(store.getState().ui.columnWidths).toEqual({});
    });
});
