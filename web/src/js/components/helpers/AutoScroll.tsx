import { RefObject } from "react";

export const isAtBottom = (viewport: RefObject<HTMLElement | null>) => {
    const v = viewport.current;
    if (v === null) {
        return false;
    }
    if (v.scrollTop === 0) {
        // We're at the top
        return false;
    }
    return Math.ceil(v.scrollTop) + v.clientHeight >= v.scrollHeight;
};

export const adjustScrollTop = (viewport: RefObject<HTMLElement | null>) => {
    if (viewport.current && !isAtBottom(viewport)) {
        viewport.current.scrollTop = viewport.current.scrollHeight;
    }
};
