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

                sendData('page_data',{"_cumulativeLayoutShift": cumulativeLayoutShift});
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
                    sendData('page_data', { "_firstInputDelay": delay });
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
                        sendData('page_data', {"_firstPaint": firstPaintTime});
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

    function observeAndSaveActions() {
        document.addEventListener('click', function(event) {
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
                    tagName: element.tagName,
                    xpath: getElementXPath(element),
                    dataAttributes: dataAttributesStr,
                    form: element?.form?.name || null,
                    content: contentValue
                };

                Object.keys(actionObj).forEach((k) => actionObj[k] == null && delete actionObj[k]);
                actions.push(actionObj);
                sendData('page_actions', actions);

            }
        }, true);
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
            let vids = querySelectorWithShadows('video');
            for (let video of vids) {
                video.addEventListener('play', sendVideoData);
                video.addEventListener('pause', sendVideoData);

                video.addEventListener("stalled", (event) => {
                    this.stallCount = this.stallCount ? this.stallCount + 1 : 1;
                });
                video.addEventListener("waiting", (event) => {
                    this.waitingCount = this.waitingCount ? this.waitingCount + 1 : 1;
                });
                video.addEventListener("error", (event) => {
                    this.errorCount = this.errorCount ? this.errorCount + 1 : 1;
                });

                let vidQuality = video.getVideoPlaybackQuality();

                let vid = {
                                src: video.src,
                                bufferedPercent: calculateBufferedPercent(video),
                                filename: (video.src == '') ? '' : new URL(video.src).pathname.split('/').pop(),
                                stallCount: video.stallCount || 0,
                                videoDecodedByteCount: getVideoDecodedByteCount(video),
                                audioBytesDecoded:  getAudioDecodedByteCount(video),
                                waitingCount: video.waitingCount || 0,
                                errorCount: video.errorCount || 0,
                                droppedVideoFrames: vidQuality.droppedVideoFrames,
                                totalVideoFrames: vidQuality.totalVideoFrames
                            };
                videos.push(vid);
            }
            return videos;
        }
        catch (e) {
            console.log(`Failed getting playback quality ${e}`, e);
            return [];
        }
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
        closeHandled = true;
        let data  = {...pageData(), ...videoData()}
        sendData('page_complete', data);
    }
    function instrumentationURL() {
        let protocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
        let url = protocol + window.location.host + '/BrowserUpData';
        return url;
    }

    function connectWebSocket() {
        try {
            const proxyURL = instrumentationURL()
            console.log('Connecting to BrowserUp Page Info WebSocket ' + proxyURL);
            proxyWs = new WebSocket(proxyURL);
        }
        catch (e) {
            console.log('Failed to create WebSocket for BrowserUp Page Info', e);
        }
        proxyWs.onopen = () => {
            console.log('WebSocket connected');
            reconnectInterval = 50;  // Reset reconnect interval on successful connection
        };

        proxyWs.onclose = (event) => {
            if (event.wasClean) {
                console.log(`WebSocket closed cleanly, code=${event.code}, reason=${event.reason}`);
            } else {
                console.log('WebSocket died');
            }
            setTimeout(connectWebSocket, reconnectInterval);
            reconnectInterval = Math.min(maxReconnectInterval, reconnectInterval * reconnectMultiplier);
        };
    }

    function sendVideoData() {
        const videoInfo = videoData();
        if (videoInfo.length === 0) {
            console.log('No videos found');
            return;
        }
        sendData('videos', videoData());
    }
    function sendPageData() {
        console.log(videoData());
        sendData('page_data', pageData());

    }

    function sendData(action, data) {
        Object.keys(data).forEach(key => data[key] === undefined ? delete data[key] : {});
        let payload = { action: action, data: data };
        if (proxyWs.readyState === WebSocket.OPEN) {
            proxyWs.send(JSON.stringify(payload));
        } else {
            console.error("WebSocket is not open. Cannot send data.");
        }
    }

    let actions = [];
    let videoDataIntervalId;
    let proxyWs;
    let reconnectInterval = 500;
    let maxReconnectInterval = 5000;
    let reconnectMultiplier = 1.5;
    let closeHandled = false;

    function init() {
        if (window.browserUp) { console.error('BrowserUp Double load Error!!!'); return; }
        connectWebSocket();
        observeAndSaveFirstPaint();
        observeAndSaveFirstInputDelay();
        observeAndSaveCumulativeLayoutShift();
        observeAndSaveActions();

        window.addEventListener('click', sendPageData);
        window.addEventListener('beforeunload', handleClose);
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'hidden') { handleClose(); }
        });
        videoDataIntervalId = setInterval(sendVideoData, 15000);
    }

    init();
})();
