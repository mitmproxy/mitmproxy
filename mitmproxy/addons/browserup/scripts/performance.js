function inIframe () { try { return window.self !== window.top; } catch (e) { return true; } }
function postPerf(){
    if (inIframe()) { return };
    var paint = {};
    performance.getEntriesByType('paint').forEach(function(element) { paint[element.name] = element.startTime});
    var perf = performance.getEntriesByType('navigation')[0];

    data = {
        pageTimings: {
                "onContentLoad": Math.round(perf.domContentLoadedEventEnd - perf.unloadEventEnd),
                "onLoad": Math.round(perf.loadEventEnd - perf.requestStart),
                "_dns": Math.round(perf.domainLookupEnd - perf.domainLookupStart),
                "_request": Math.round(perf.responseStart - perf.requestStart),
                "_tcp": Math.round(perf.connectEnd - perf.connectStart),
                "_ssl": Math.round(perf.requestStart - perf.secureConnectionStart),
                "_TTFB": Math.round(perf.responseStart - perf.requestStart),
                "_domComplete": Math.round(perf.domComplete - perf.requestStart),
                "_domInteractive": Math.round(perf.domInteractive - perf.requestStart),
                "_renderTime": Math.round(perf.domComplete - perf.domContentLoadedEventEnd),
                "_firstPaint": Math.round(paint["first-paint"]),
                "_firstContentfulPaint": Math.round(paint["first-contentful-paint"])
                }
    }
    console.log(JSON.stringify(data, null, 2));
    if ('sendBeacon' in navigator) {
        if (navigator.sendBeacon("{{URL}}", data)) {
        } else { console.error("BrowserUpProxy sendbeacon error") }
    }
}
postPerf();