import { Comparer } from "@reduxjs/toolkit";

type Item = { id: string };

export function buildIndex<T extends Item>(
    data: T[],
): { [id: string]: number } {
    return Object.fromEntries(data.map((f, i) => [f.id, i]));
}

export function buildLookup<T extends Item>(
    data: T[],
): { [id: string]: boolean } {
    return Object.fromEntries(data.map((f) => [f.id, true]));
}

export function withKeyRemoved<T extends object>(map: T, key: string): T {
    if (key in map) {
        map = { ...map };
        delete map[key];
    }
    return map;
}

export function removeViewItemAt<T extends Item>(
    prevView: T[],
    prevViewIndex: { [id: string]: number },
    pos: number,
) {
    // update data
    const view = prevView.toSpliced(pos, 1);

    // update index
    const _viewIndex = { ...prevViewIndex };
    delete _viewIndex[prevView[pos].id];
    for (let i = view.length - 1; i >= pos; i--) {
        _viewIndex[view[i].id] = i;
    }

    return { view, _viewIndex };
}

export function updateViewItem<T extends Item>(
    prevView: T[],
    prevViewIndex: { [id: string]: number },
    item: T,
    sort: Comparer<T>,
) {
    const view = [...prevView];
    const _viewIndex = { ...prevViewIndex };
    let pos = _viewIndex[item.id];
    view[pos] = item;
    while (pos + 1 < view.length && sort(view[pos], view[pos + 1]) > 0) {
        view[pos] = view[pos + 1];
        view[pos + 1] = item;
        _viewIndex[item.id] = pos + 1;
        _viewIndex[view[pos].id] = pos;
        ++pos;
    }
    while (pos > 0 && sort(view[pos], view[pos - 1]) < 0) {
        view[pos] = view[pos - 1];
        view[pos - 1] = item;
        _viewIndex[item.id] = pos - 1;
        _viewIndex[view[pos].id] = pos;
        --pos;
    }
    return { view, _viewIndex };
}

export function insertViewItem<T extends Item>(
    prevView: T[],
    prevViewIndex: { [id: string]: number },
    item: T,
    sort: Comparer<T>,
) {
    const pos = findInsertPos(prevView, item, sort);

    const view = prevView.toSpliced(pos, 0, item);

    const _viewIndex = { ...prevViewIndex };
    for (let i = view.length - 1; i >= pos; i--) {
        _viewIndex[view[i].id] = i;
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
    if (sort(list[high - 1], item) <= 0) {
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
