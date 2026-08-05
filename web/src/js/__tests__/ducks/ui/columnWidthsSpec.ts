import reducer, {
    clearColumnWidths,
    commitColumnWidths,
    loadColumnWidths,
    resetColumnWidths,
    setColumnWidths,
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
