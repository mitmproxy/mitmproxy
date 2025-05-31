import {
    buildIndex,
    buildLookup,
    findInsertPos,
    insertViewItem,
    removeViewItemAt,
    updateViewItem,
    withElemRemoved,
} from "../../../ducks/flows/_utils";
import { Comparer } from "@reduxjs/toolkit";

test("buildIndex", () => {
    expect(buildIndex([{ id: "foo" }, { id: "bar" }])).toEqual(
        new Map([
            ["foo", 0],
            ["bar", 1],
        ]),
    );
});

test("buildLookup", () => {
    expect(buildLookup([{ id: "foo" }, { id: "bar" }])).toEqual(
        new Set(["foo", "bar"]),
    );
});

test("withElemRemoved", () => {
    const s = new Set(["foo", "bar"]);
    expect(withElemRemoved(s, "baz")).toBe(s);

    const r = withElemRemoved(s, "bar");
    // not in-place
    expect(r).not.toBe(s);
    expect(r).toEqual(new Set(["foo"]));
});

test("removeViewItemAt", () => {
    const v = [{ id: "a" }, { id: "b" }, { id: "c" }];
    const idx = new Map([
        ["a", 0],
        ["b", 1],
        ["c", 2],
    ]);
    // not in-place
    expect(removeViewItemAt(v, idx, 0).view).not.toBe(v);
    expect(removeViewItemAt(v, idx, 0)._viewIndex).not.toBe(idx);

    expect(removeViewItemAt(v, idx, 0)).toEqual({
        view: [{ id: "b" }, { id: "c" }],
        _viewIndex: new Map([
            ["b", 0],
            ["c", 1],
        ]),
    });
    expect(removeViewItemAt(v, idx, 1)).toEqual({
        view: [{ id: "a" }, { id: "c" }],
        _viewIndex: new Map([
            ["a", 0],
            ["c", 1],
        ]),
    });
    expect(removeViewItemAt(v, idx, 2)).toEqual({
        view: [{ id: "a" }, { id: "b" }],
        _viewIndex: new Map([
            ["a", 0],
            ["b", 1],
        ]),
    });
});

test("updateViewItem", () => {
    type Elem = { id: string; w: number };
    const v = [
        { id: "a", w: 1 },
        { id: "b", w: 2 },
        { id: "c", w: 3 },
    ];
    const idx = new Map([
        ["a", 0],
        ["b", 1],
        ["c", 2],
    ]);
    const sort: Comparer<Elem> = (a, b) => a.w - b.w;
    // not in-place
    expect(updateViewItem(v, idx, { id: "a", w: 5 }, sort).view).not.toBe(v);
    expect(updateViewItem(v, idx, { id: "a", w: 5 }, sort)._viewIndex).not.toBe(
        idx,
    );

    expect(updateViewItem(v, idx, { id: "b", w: 1.5 }, sort)).toEqual({
        view: [
            { id: "a", w: 1 },
            { id: "b", w: 1.5 },
            { id: "c", w: 3 },
        ],
        _viewIndex: new Map([
            ["a", 0],
            ["b", 1],
            ["c", 2],
        ]),
    });
    expect(updateViewItem(v, idx, { id: "b", w: 0 }, sort)).toEqual({
        view: [
            { id: "b", w: 0 },
            { id: "a", w: 1 },
            { id: "c", w: 3 },
        ],
        _viewIndex: new Map([
            ["b", 0],
            ["a", 1],
            ["c", 2],
        ]),
    });
    expect(updateViewItem(v, idx, { id: "b", w: 4 }, sort)).toEqual({
        view: [
            { id: "a", w: 1 },
            { id: "c", w: 3 },
            { id: "b", w: 4 },
        ],
        _viewIndex: new Map([
            ["a", 0],
            ["c", 1],
            ["b", 2],
        ]),
    });
    expect(updateViewItem(v, idx, { id: "c", w: 0 }, sort)).toEqual({
        view: [
            { id: "c", w: 0 },
            { id: "a", w: 1 },
            { id: "b", w: 2 },
        ],
        _viewIndex: new Map([
            ["c", 0],
            ["a", 1],
            ["b", 2],
        ]),
    });
});

test("insertViewItem", () => {
    type Elem = { id: string };
    const v = [{ id: "b" }, { id: "d" }];
    const idx = new Map([
        ["b", 0],
        ["d", 1],
    ]);
    const sort: Comparer<Elem> = (a, b) => a.id.localeCompare(b.id);
    // not in-place
    expect(insertViewItem(v, idx, { id: "a" }, sort).view).not.toBe(v);
    expect(insertViewItem(v, idx, { id: "a" }, sort)._viewIndex).not.toBe(idx);

    expect(insertViewItem(v, idx, { id: "a" }, sort)).toEqual({
        view: [{ id: "a" }, { id: "b" }, { id: "d" }],
        _viewIndex: new Map([
            ["a", 0],
            ["b", 1],
            ["d", 2],
        ]),
    });
    expect(insertViewItem(v, idx, { id: "c" }, sort)).toEqual({
        view: [{ id: "b" }, { id: "c" }, { id: "d" }],
        _viewIndex: new Map([
            ["b", 0],
            ["c", 1],
            ["d", 2],
        ]),
    });
    expect(insertViewItem(v, idx, { id: "e" }, sort)).toEqual({
        view: [{ id: "b" }, { id: "d" }, { id: "e" }],
        _viewIndex: new Map([
            ["b", 0],
            ["d", 1],
            ["e", 2],
        ]),
    });
});

test("findInsertPos", () => {
    expect(findInsertPos([2, 4, 6], 1, (a, b) => a - b)).toEqual(0);
    expect(findInsertPos([2, 4, 6], 3, (a, b) => a - b)).toEqual(1);
    expect(findInsertPos([2, 4, 6], 5, (a, b) => a - b)).toEqual(2);
    expect(findInsertPos([2, 4, 6], 7, (a, b) => a - b)).toEqual(3);

    // no sort -> append to end
    expect(findInsertPos([1, 2, 4], 3, () => 0)).toEqual(3);

    // empty
    expect(findInsertPos([], 42, () => 0)).toEqual(0);
});
