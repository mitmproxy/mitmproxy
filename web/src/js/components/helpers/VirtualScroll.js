/**
 * Calculate virtual scroll stuffs
 *
 * @param {?Object} opts Options for calculation
 *
 * @returns {Object} result
 *
 * __opts__ should have following properties:
 * - {number}         itemCount
 * - {number}         rowHeight
 * - {number}         viewportTop
 * - {number}         viewportHeight
 * - {Array<?number>} [itemHeights]
 *
 * __result__ have following properties:
 * - {number} start
 * - {number} end
 * - {number} paddingTop
 * - {number} paddingBottom
 */
export function calcVScroll(opts) {
    if (!opts) {
        return { start: 0, end: 0, paddingTop: 0, paddingBottom: 0 };
    }

    const { itemCount, rowHeight, viewportTop, viewportHeight, itemHeights } = opts;
    const viewportBottom = viewportTop + viewportHeight;

    let start = 0;
    let end = 0;

    let paddingTop = 0;
    let paddingBottom = 0;

    if (itemHeights) {

        for (let i = 0, pos = 0; i < itemCount; i++) {
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

    } else {

        // Make sure that we start at an even row so that CSS `:nth-child(even)` is preserved
        start = Math.max(0, Math.floor(viewportTop / rowHeight) - 1) & ~1;
        end = Math.min(
            itemCount,
            start + Math.ceil(viewportHeight / rowHeight) + 2
        );

        // When a large trunk of elements is removed from the button, start may be far off the viewport.
        // To make this issue less severe, limit the top placeholder to the total number of rows.
        paddingTop = Math.min(start, itemCount) * rowHeight;
        paddingBottom = Math.max(0, itemCount - end) * rowHeight;
    }

    return { start, end, paddingTop, paddingBottom };
}
