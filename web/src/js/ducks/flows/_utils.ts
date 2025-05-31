import { Comparer } from "@reduxjs/toolkit";
import { toSpliced } from "./_compat";

type Item = { id: string };

export function buildIndex<T extends Item>(data: T[]): Map<string, number> {
    return new Map(data.map((f, i) => [f.id, i]));
}

export function buildLookup<T extends Item>(data: T[]): Set<string> {
    return new Set(data.map((f) => f.id));
}

export function withElemRemoved<K>(set: Set<K>, key: K): Set<K> {
    if (set.has(key)) {
        set = new Set(set);
        set.delete(key);
    }
    return set;
}

export function removeViewItemAt<T extends Item>(
    prevView: T[],
    prevViewIndex: Map<string, number>,
    pos: number,
): { view: T[]; _viewIndex: Map<string, number> } {
    // update data
    const view = toSpliced(prevView, pos, 1);

    // update index
    const _viewIndex = new Map(prevViewIndex);
    _viewIndex.delete(prevView[pos].id);
    for (let i = view.length - 1; i >= pos; i--) {
        _viewIndex.set(view[i].id, i);
    }

    return { view, _viewIndex };
}

export function updateViewItem<T extends Item>(
    prevView: T[],
    prevViewIndex: Map<string, number>,
    item: T,
    sort: Comparer<T>,
): { view: T[]; _viewIndex: Map<string, number> } {
    const view = [...prevView];
    const len = view.length;
    let _viewIndex = prevViewIndex,
        pos = _viewIndex.get(item.id)!;

    // is this overoptimized? yes.
    // was it fun? also yes.
    if (pos + 1 < len && sort(item, view[pos + 1]) > 0) {
        // move up
        _viewIndex = new Map(_viewIndex);
        do {
            const move = view[pos + 1];
            view[pos] = move;
            _viewIndex.set(move.id, pos);
            pos++;
        } while (pos + 1 < len && sort(item, view[pos + 1]) > 0);
        _viewIndex.set(item.id, pos);
    } else if (pos > 0 && sort(item, view[pos - 1]) < 0) {
        // move down
        _viewIndex = new Map(_viewIndex);
        do {
            const move = view[pos - 1];
            view[pos] = move;
            _viewIndex.set(move.id, pos);
            pos--;
        } while (pos > 0 && sort(item, view[pos - 1]) < 0);
        _viewIndex.set(item.id, pos);
    }
    view[pos] = item;

    return { view, _viewIndex };
}

export function insertViewItem<T extends Item>(
    prevView: T[],
    prevViewIndex: Map<string, number>,
    item: T,
    sort: Comparer<T>,
): { view: T[]; _viewIndex: Map<string, number> } {
    const pos = findInsertPos(prevView, item, sort);

    const view = toSpliced(prevView, pos, 0, item);

    const _viewIndex = new Map(prevViewIndex);
    for (let i = view.length - 1; i >= pos; i--) {
        _viewIndex.set(view[i].id, i);
    }

    return { view, _viewIndex };
}

/// Find the insertion position in a sorted array.
export function findInsertPos<T>(
    list: T[],
    item: T,
    sort: Comparer<T>,
): number {
    let low = 0,
        high = list.length;

    // fast path: insert at end
    if (high === 0 || sort(list[high - 1], item) <= 0) {
        return high;
    }

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
