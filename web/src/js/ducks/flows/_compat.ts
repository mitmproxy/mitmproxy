// compatibility shim for nodejs < 20 (Ubuntu 24.04 LTS)
import { type Comparer } from "@reduxjs/toolkit";

export function toSorted<T>(data: T[], sort: Comparer<T>): T[] {
    if (data.toSorted) {
        return data.toSorted(sort);
    } else {
        return [...data].sort(sort);
    }
}

export function toSpliced<T>(
    data: T[],
    ...args: [start: number, deleteCount: number, ...T[]]
): T[] {
    if (data.toSpliced) {
        return data.toSpliced(...args);
    } else {
        const ret = [...data];
        ret.splice(...args);
        return ret;
    }
}
