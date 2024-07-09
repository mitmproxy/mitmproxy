type VScrollArgs = {
    itemCount: number;
    rowHeight: number;
    viewportTop: number;
    viewportHeight: number;
    itemHeights?: number[];
};

export type VScroll = {
    start: number;
    end: number;
    paddingTop: number;
    paddingBottom: number;
};

export function calcVScroll(
    opts: VScrollArgs | undefined = undefined,
): VScroll {
    if (!opts) {
        return { start: 0, end: 0, paddingTop: 0, paddingBottom: 0 };
    }

    const { itemCount, rowHeight, viewportTop, viewportHeight, itemHeights } =
        opts;
    const viewportBottom = viewportTop + viewportHeight;

    let start = 0,
        end = 0,
        paddingTop = 0,
        paddingBottom = 0;

    if (itemHeights) {
        let pos = 0;
        for (let i = 0; i < itemCount; i++) {
            const height = itemHeights[i] || rowHeight;

            if (pos <= viewportTop && i % 2 === 0) {
                paddingTop = pos;
                start = i;
            }

            if (pos <= viewportBottom) {
                end = i + 1;
            } else {
                paddingBottom += height;
            }

            pos += height;
        }
        // viewportTop + viewportHeight is larger than our total table height.
        // this means that rows have been freshly removed and we need to calculate with
        // an updated (smaller) viewportTop.
        if (viewportTop > 0 && pos < viewportTop + viewportHeight)
            return calcVScroll({
                itemCount,
                rowHeight,
                viewportTop: pos - viewportHeight,
                viewportHeight,
                itemHeights,
            });
    } else {
        // We may have removed a lot of rows since the last render,
        // which means viewportTop will move up.
        const newViewportTop = Math.min(
            viewportTop,
            Math.max(0, itemCount * rowHeight - viewportHeight),
        );

        // Make sure that we start at an even row so that CSS `:nth-child(even)` is preserved
        start = Math.max(0, Math.floor(newViewportTop / rowHeight) - 1) & ~1;
        end = Math.min(
            itemCount,
            start + Math.ceil(viewportHeight / rowHeight) + 2,
        );

        paddingTop = start * rowHeight;
        paddingBottom = (itemCount - end) * rowHeight;
    }

    return { start, end, paddingTop, paddingBottom };
}
