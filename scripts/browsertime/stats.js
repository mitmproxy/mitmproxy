function cumulativeLayoutShift() {
    const supported = PerformanceObserver.supportedEntryTypes;
    if (!supported || supported.indexOf('layout-shift') === -1) {
        return;
    }
    // See https://web.dev/layout-instability-api
    // https://github.com/mmocny/web-vitals/wiki/Snippets-for-LSN-using-PerformanceObserver#max-session-gap1s-limit5s
    let max = 0;
    let curr = 0;
    let firstTs = Number.NEGATIVE_INFINITY;
    let  prevTs = Number.NEGATIVE_INFINITY;
    const observer = new PerformanceObserver(list => {});
    observer.observe({ type: 'layout-shift', buffered: true });
    const list = observer.takeRecords();
    for (let entry of list) {
        if (entry.hadRecentInput) {
            continue;
        }
        if (entry.startTime - firstTs > 5000 || entry.startTime - prevTs > 1000) {
            firstTs = entry.startTime;
            curr = 0;
        }
        prevTs = entry.startTime;
        curr += entry.value;
        max = Math.max(max, curr);
    }
    return max;
}

function timeToFirstInteractive() {
    // Firefox only TTFI
    // need pref to be activated
    // If the "event" has happend, it will return 0
    const timing = window.performance.timing;
    if (timing.timeToFirstInteractive && timing.timeToFirstInteractive > 0) {
        const ttfi = Number(
            (timing.timeToFirstInteractive - timing.navigationStart).toFixed(0)
        );
        // We have seen cases when TTFI is - 46 years.
        if (ttfi < 0) {
            return 0;
        } else {
            return ttfi;
        }
    } else return undefined;
}

function timetoDomContentFlushed() {
    // Firefox only timeToDOMContentFlushed
    // need pref to be activated
    const timing = window.performance.timing;
    if (timing.timeToDOMContentFlushed) {
        return Number(
            (timing.timeToDOMContentFlushed - timing.navigationStart).toFixed(0)
        );
    }
    else return undefined;
}

function largestContentFulPaint() {
    // https://gist.github.com/karlgroves/7544592
    function getDomPath(el) {
        const stack = [];
        while ( el.parentNode != null ) {
            let sibCount = 0;
            let sibIndex = 0;
            for ( let i = 0; i < el.parentNode.childNodes.length; i++ ) {
                let sib = el.parentNode.childNodes[i];
                if ( sib.nodeName == el.nodeName ) {
                    if ( sib === el ) {
                        sibIndex = sibCount;
                    }
                    sibCount++;
                }
            }
            if ( el.hasAttribute && el.hasAttribute('id') && el.id != '' ) {
                stack.unshift(el.nodeName.toLowerCase() + '#' + el.id);
            } else if ( sibCount > 1 ) {
                stack.unshift(el.nodeName.toLowerCase() + ':eq(' + sibIndex + ')');
            } else {
                stack.unshift(el.nodeName.toLowerCase());
            }
            el = el.parentNode;
        }

        return stack.slice(1);
    }

    const supported = PerformanceObserver.supportedEntryTypes;
    if (!supported || supported.indexOf('largest-contentful-paint') === -1) {
        return;
    }
    const observer = new PerformanceObserver(list => {});
    observer.observe({ type: 'largest-contentful-paint', buffered: true });
    const entries = observer.takeRecords();
    if (entries.length > 0) {
        const largestEntry = entries[entries.length - 1];
        return {
            duration: largestEntry.duration,
            id: largestEntry.id,
            url: largestEntry.url,
            loadTime: Number(largestEntry.loadTime.toFixed(0)),
            renderTime: Number(Math.max(largestEntry.renderTime,largestEntry.loadTime).toFixed(0)),
            size: largestEntry.size,
            startTime: Number(largestEntry.startTime.toFixed(0)),
            tagName: largestEntry.element ? largestEntry.element.tagName : '',
            className :largestEntry.element ? largestEntry.element.className : '',
            domPath:  largestEntry.element ? (getDomPath(largestEntry.element)).join( ' > ') : '',
            tag: largestEntry.element ? (largestEntry.element.cloneNode(false)).outerHTML : ''
        };
    } else return;
}
