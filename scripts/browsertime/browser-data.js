// Change summary for BrowserTime APACHE items from this folder:
// Scripts from: https://github.com/sitespeedio/browsertime/tree/main/browserscripts
// were consolidated here for a JSON summary payload including core vitals data.  https://web.dev/vitals/
// Alternative:  https://zizzamia.github.io/perfume/
/* jshint esversion: 11 */
(function() {
    function inIframe () { try { return window.self !== window.top; } catch (e) { return true; } }

    // cumulative layout shift can continue to change after page load, so we need to observe
    function observeAndSaveCumulativeLayoutShift() {
        try {
            const supported = PerformanceObserver.supportedEntryTypes;
            if (!supported || supported.indexOf('layout-shift') === -1) { return; }
            let cumulativeLayoutShift = 0;
            let curr = 0;
            let firstTs= Number.NEGATIVE_INFINITY;
            let prevTs = Number.NEGATIVE_INFINITY;

            const observer = new PerformanceObserver((list) => {
                for (let entry of list.getEntries()) {
                    if (entry.hadRecentInput) {
                        continue;
                    }
                    if (entry.startTime - firstTs > 5000 || entry.startTime - prevTs > 1000) {
                        firstTs = entry.startTime;
                        curr = 0;
                    }
                    prevTs = entry.startTime;
                    curr += entry.value;
                    cumulativeLayoutShift = Math.max(cumulativeLayoutShift, curr);
                }

                sendData('page_timings', {"_cumulativeLayoutShift": cumulativeLayoutShift});
            });
            observer.observe({type: 'layout-shift', buffered: true});
        } catch (e)  {
            console.log('Failed to create observer for cumulative layout shift');
        }
    }

    function observeAndSaveFirstInputDelay() {
        try {
            // note, may need updating for iframes, can use code here:  https://github.com/GoogleChrome/web-vitals
            const supported = PerformanceObserver.supportedEntryTypes;
            if (!supported || supported.indexOf("first-input") === -1) { return; }
            new PerformanceObserver((entryList) => {
                for (let entry of entryList.getEntries()) {
                    let delay = Number((entry.processingStart - entry.startTime).toFixed(1));
                    sendData('page_timings', { "_firstInputDelay": delay });
                }
            }).observe({type: 'first-input', buffered: true});
        } catch (e) {
            console.log('Failed to create observer for first input delay');
        }
    }

    function largestContentfulPaint() {
        try {
            let result = {startTime: -1, size: -1, domPath: "", tag: ""};
            const supported = PerformanceObserver.supportedEntryTypes;
            if (!supported || supported.indexOf('largest-contentful-paint') === -1) { return result; }
            let observer = new PerformanceObserver(list => {
            });
            observer.observe({type: 'largest-contentful-paint', buffered: true});
            let entries = observer.takeRecords();
            let candidates = [];
            for (let entry of entries) {
                let element = entry.element;
                candidates.push({
                    duration: entry.duration,
                    id: entry.id,
                    url: entry.url,
                    loadTime: Number(entry.loadTime.toFixed(0)),
                    renderTime: Number(Math.max(entry.renderTime, entry.loadTime).toFixed(0)),
                    size: entry.size,
                    startTime: Number(entry.startTime.toFixed(0)),
                    tagName: element ? element.tagName : '',
                    className: element ? element.className : '',
                    domPath: element ? (getDomPath(element)).join(' > ') : '',
                    tag: element ? (element.cloneNode(false)).outerHTML : ''
                });
            }
            let lcp = candidates.pop() || {};
            result.startTime = lcp.startTime || result.startTime;
            result.size = lcp.size || result.size;
            result.domPath = lcp.domPath || result.domPath;
            result.tag = lcp.tag || result.tag;
            return result;
        } catch (e) {
            console.log('Failed getting largest contentful paint');
        }
    }

    function navTimings() {
        try {
            let t = window.performance.getEntriesByType('navigation')[0];
            let d = 0;
            if (t) {
                return {
                    domainLookupTime: Number((t.domainLookupEnd - t.domainLookupStart).toFixed(d)),
                    ttfb: Math.round(t.responseStart - t.requestStart),
                    redirectionTime: Number((t.redirectEnd - t.redirectStart).toFixed(d)),
                    serverConnectionTime: Number((t.connectEnd - t.connectStart).toFixed(d)),
                    serverResponseTime: Number((t.responseEnd - t.requestStart).toFixed(d)),
                    pageDownloadTime: Number((t.responseEnd - t.responseStart).toFixed(d)),
                    domInteractiveTime: Number(t.domInteractive.toFixed(d)),
                    domContentLoadedTime: Number(t.domContentLoadedEventStart.toFixed(d)),
                    pageLoadTime: Number(t.loadEventStart.toFixed(d)),
                    frontEndTime: Number((t.loadEventStart - t.responseEnd).toFixed(d)),
                    backEndTime: Number(t.responseStart.toFixed(d))
                };
            } else {
                // Safari
                t = window.performance.timing;
                return {
                    domainLookupTime: t.domainLookupEnd - t.domainLookupStart,
                    redirectionTime: t.fetchStart - t.navigationStart,
                    serverConnectionTime: t.connectEnd - t.connectStart,
                    serverResponseTime: t.responseEnd - t.requestStart,
                    pageDownloadTime: t.responseEnd - t.responseStart,
                    domInteractiveTime: t.domInteractive - t.navigationStart,
                    domContentLoadedTime: t.domContentLoadedEventStart - t.navigationStart,
                    pageLoadTime: t.loadEventStart - t.navigationStart,
                    frontEndTime: t.loadEventStart - t.responseEnd,
                    backEndTime: t.responseStart - t.navigationStart,
                    ttfb: t.responseStart - t.requestStart
                };
            }
        } catch (e) {
            console.log('Failed getting navigation timings');
            return {};
        }
    }

    function observeAndSaveFirstPaint() {
        try {
            const observer = new PerformanceObserver((list) => {
                let firstPaintTime;
                for (const entry of list.getEntries()) {
                    if (entry.name === 'first-paint') {
                        firstPaintTime = entry.startTime.toFixed(0);
                        sendData('page_timings', {"_firstPaint": firstPaintTime});
                    }
                }
            });
            observer.observe({entryTypes: ['paint']});
        } catch (e) {
            console.log('Failed to create observer for observeFirstPaint', e);
        }
    }

    function pageData(){
        try {
            if (inIframe()) { return; }
            let paint = {};
            performance.getEntriesByType('paint').forEach(function (element) {
                paint[element.name] = element.startTime;
            });
            const perf = performance.getEntriesByType('navigation')[0];
            const n = navTimings();

            return {
                "title": window.document.title,
                "onContentLoad": n.domContentLoadedTime || -1,
                "onLoad": n.pageLoadTime || -1,
                "_href": window.location.href,
                "_dns": Math.round(perf.domainLookupEnd - perf.domainLookupStart) || -1,
                "_ssl": Math.round(perf.requestStart - perf.secureConnectionStart) || -1,
                "_timeToFirstByte": n.ttfb || -1,
                "_largestContentfulPaint":  largestContentfulPaint() || -1,
                "_firstContentfulPaint": Math.round(paint["first-contentful-paint"]) || -1,
                "_domInteractive": n.domInteractiveTime || -1
            };
        } catch (e) {
            console.log(`Failed getting page timings`, e);
            return {};
        }
    }


    function getDomPath(el) {
        let stack = [];
        while (el.parentNode != null) {
            let nodeNameLower = el.nodeName.toLowerCase();
            let siblingIndex = 0;
            let siblingCount = 0;
            for (let i = 0; i < el.parentNode.childNodes.length; i++) {
                let sibling = el.parentNode.childNodes[i];
                if (sibling.nodeName == el.nodeName) {
                    if (sibling === el) { siblingIndex = siblingCount; break; }
                    siblingCount++;
                }
            }

            if (el.hasAttribute('id') && el.id != '') {
                stack.unshift(nodeNameLower + '#' + el.id);
            } else if (siblingCount > 1) {
                stack.unshift(nodeNameLower + ':eq(' + siblingIndex + ')');
            } else {
                stack.unshift(nodeNameLower);
            }
            el = el.parentNode;
        }
        return stack.slice(1);
    }


    function getElementXPath(element) {
        let paths = [];
        for (; element && element.nodeType == 1; element = element.parentNode) {
            let index = 0;
            for (let sibling = element.previousSibling; sibling; sibling = sibling.previousSibling) {
                if (sibling.nodeType == 1 && sibling.tagName == element.tagName) {
                    index++;
                }
            }
            let tagName = element.tagName.toLowerCase();
            let pathIndex = (index ? "[" + (index + 1) + "]" : "");
            paths.splice(0, 0, tagName + pathIndex);
        }
        return paths.length ? "/" + paths.join("/") : null;
    }

    function observeAndSaveActions() {
        document.addEventListener('change', function(event) { captureAction(event); }, true);
        document.addEventListener('click', function(event) { captureAction(event); }, true);
    }

    function captureAction(event) {
        let element = event.target;
        if (element) {
            let dataAttributesArr = [];
            const pattern = /test|qa|cy|play|sele|autom|name|id|browserup/i;

            for (let attr of element.attributes) {
                if (attr.name.startsWith('data-') && pattern.test(attr.name)) {
                    dataAttributesArr.push(`${attr.name}=${attr.value.substring(0, 50)}`);
                }
            }

            let dataAttributesStr = dataAttributesArr.join(',');
            let contentValue = (element.value || element.innerText).trim();
            contentValue = contentValue.length > 50 ? contentValue.substring(0, 50) : contentValue;

            let actionObj = {
                name: element.getAttribute('name') || null,
                id: element.getAttribute('id') || null,
                className: element.getAttribute('class') || null,
                ariaLabel: element.getAttribute('aria-label') || null,
                tagName: element.tagName,
                event: event.type,
                role: element.getAttribute('role'),
                xpath: getElementXPath(element),
                dataAttributes: dataAttributesStr,
                form: element?.form?.name || null,
                content: contentValue
            };

            Object.keys(actionObj).forEach((k) => actionObj[k] == null && delete actionObj[k]);
            actions.push(actionObj);
        }
    }

    function getAbsoluteURL(baseURL, relativePath) {
        try {
            if (!relativePath) return relativePath; // Return the same value if path is null or empty
            // Create a URL object with base URL and the relative path
            const urlObj = new URL(relativePath, baseURL);
            return urlObj.href; // Return the absolute URL
        } catch (e) {
            console.error(e);
            return relativePath;
        }
    }

    function getVideoDecodedByteCount(video) {
        if ('webkitVideoDecodedByteCount' in video) {
            return video.webkitVideoDecodedByteCount;
        }
        return -1;
    }

    function getAudioDecodedByteCount(video) {
        if ('webkitAudioDecodedByteCount' in video) {
            return video.webkitAudioDecodedByteCount;
        }
        return -1;
    }

    function querySelectorWithShadows(selector, el = document.body) {
        const childShadows = Array.from(el.querySelectorAll('*')).
        map(el => el.shadowRoot).filter(Boolean);
        const childResults = childShadows.map(child => querySelectorWithShadows(selector, child));
        const result = Array.from(el.querySelectorAll(selector));
        return result.concat(childResults).flat();
    }

    function videoData() {
        try {
            let videos = [];
            const vids = querySelectorWithShadows('video'); // Assuming this function is implemented elsewhere to query shadow DOM

            for (let video of vids) {
                video.addEventListener('play', sendVideoData);
                video.addEventListener('pause', sendVideoData);

                video.addEventListener("stalled", function(event) {
                    this.stallCount = this.stallCount ? this.stallCount + 1 : 1;
                });
                video.addEventListener("waiting", function(event) {
                    this.waitingCount = this.waitingCount ? this.waitingCount + 1 : 1;
                });
                video.addEventListener("error", function(event) {
                    this.errorCount = this.errorCount ? this.errorCount + 1 : 1;
                });

                let vidQuality = video.getVideoPlaybackQuality();
                let sources = video.querySelectorAll('source');

                if (sources.length === 0) {
                    // No <source> tags, use src property from video tag
                    if (isValidSrc(video.src)) {
                        let vid = buildVideoObject(video.src, video, vidQuality);
                        videos.push(vid);
                    }
                } else {
                    // for each source, get the src and build a video object
                    for (let source of sources) {
                        console.log(source);
                        let src = source.src;
                        if (isValidSrc(src)) {
                            let vid = buildVideoObject(src, video, vidQuality);
                            videos.push(vid);
                        }
                    }

                }
            }
            console.log("VIDEOS --->", videos );
            return videos;
        }
        catch (e) {
            console.log(`Failed getting playback quality ${e}`, e);
            return [];
        }
    }

    function isValidSrc(src) {
        return typeof src === 'string' && src.length > 1;
    }

    function buildVideoObject(src, video, vidQuality) {
        return {
            _videoSRC: getAbsoluteURL(window.location, src),
            _videoBufferedPercent: calculateBufferedPercent(video),
            _videoStallCount: video.stallCount || 0,
            _videoDecodedByteCount: getVideoDecodedByteCount(video),
            _videoWaitingCount: video.waitingCount || 0,
            _videoErrorCount: video.errorCount || 0,
            _videoDroppedFrames: vidQuality.droppedVideoFrames,
            _videoTotalFrames: vidQuality.totalVideoFrames,
            _videoAudioBytesDecoded:  getAudioDecodedByteCount(video)
        };
    }


    function calculateBufferedPercent(video) {
        try {
            const buffered = video.buffered;
            const duration = video.duration;
            if (duration === 0) return 0;

            const bufferedEnd = buffered.length ? buffered.end(buffered.length - 1) : 0;
            const result = Math.round((bufferedEnd / duration) * 100);
            return isNaN(result) ? 0 : result;
        }
        catch (e) {
            return -1;
        }
    }

    function handleClose() {
        if (closeHandled) {
            return;
        }

        let sendPromise = new Promise(function(resolve, reject) {
            sendData('page_complete', pageData());
            sendVideoData();
            sendData('actions', actions);
        });

        sendPromise.then(function() {
            if (proxyWs.readyState !== WebSocket.CLOSED) { proxyWs.close(); }
        });
        closeHandled = true;
    }
    function instrumentationURL() {
        let protocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
        let url = protocol + window.location.host + '/BrowserUpData';
        return url;
    }


    function sendVideoData() {
        const videoInfo = videoData();
        console.log(`Found ${videoInfo.length} videos per sendVideoData`);
        if (videoInfo.length === 0) { return; }
        sendData('videos', videoInfo);
    }
    function sendPageData() {
        sendData('page_timings', pageData());
    }

    let actions = [];
    let videoDataIntervalId;
    let reconnectInterval = 100;
    let maxReconnectInterval = 10000;
    let reconnectMultiplier = 2;
    let closeHandled = false;

    let proxyWs = new WebSocket(instrumentationURL());
    proxyWs.onclose = (event) => {
        if (closeHandled == true) { return; }
        setTimeout(connectWebSocket, reconnectInterval);
        reconnectInterval = Math.min(maxReconnectInterval, reconnectInterval * reconnectMultiplier);
    };

    proxyWs.onopen = function(event) {
        console.log('WebSocket connected');
        reconnectInterval = 50;  // Reset reconnect interval on successful connection
    };

    function sendData(operation, data) {
        Object.keys(data).forEach(key => data[key] === undefined ? delete data[key] : {});
        let payload = { operation: operation, data: data };
        waitForOpenSocket(proxyWs).then(_ => {
            console.log(`Sending ${operation} data to proxy`);
            proxyWs.send(JSON.stringify(payload));
        });
    }

    function waitForOpenSocket(socket) {
        return new Promise((resolve) => {
            if (socket.readyState !== socket.OPEN) {
                socket.addEventListener("open", (_) => {
                    resolve(socket);
                })
            } else {
                resolve();
            }
        });
    }

    function init() {
        if (window.browserUp) { console.error('BrowserUp Double load Error!!!'); return; }

        observeAndSaveFirstPaint();
        observeAndSaveFirstInputDelay();
        observeAndSaveCumulativeLayoutShift();
        observeAndSaveActions();
        videoDataIntervalId = setInterval(sendVideoData, 15000);

        window.addEventListener('load', sendVideoData);
        window.addEventListener('load', sendPageData);
        window.addEventListener('click', sendPageData);
        window.addEventListener('beforeunload', handleClose);
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'hidden') { handleClose(); }
        });

    }
    init();
})();
