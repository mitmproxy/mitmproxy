// http://blog.vjeux.com/2013/javascript/scroll-position-with-react.html (also contains inverse example)
var AutoScrollMixin = {
    componentWillUpdate: function () {
        var node = this.getDOMNode();
        this._shouldScrollBottom = node.scrollTop + node.clientHeight === node.scrollHeight;
    },
    componentDidUpdate: function () {
        if (this._shouldScrollBottom) {
            var node = this.getDOMNode();
            node.scrollTop = node.scrollHeight;
        }
    },
};

var StickyHeadMixin = {
    adjustHead: function () {
        // Abusing CSS transforms to set the element
        // referenced as head into some kind of position:sticky.
        var head = this.refs.head.getDOMNode();
        head.style.transform = "translate(0," + this.getDOMNode().scrollTop + "px)";
    }
};

var Key = {
    UP: 38,
    DOWN: 40,
    PAGE_UP: 33,
    PAGE_DOWN: 34,
    LEFT: 37,
    RIGHT: 39,
    ENTER: 13,
    ESC: 27,
    TAB: 9,
    SPACE: 32,
    J: 74,
    K: 75,
    H: 72,
    L: 76
};

var formatSize = function (bytes) {
    var size = bytes;
    var prefix = ["B", "KB", "MB", "GB", "TB"];
    while (size >= 1024 && prefix.length > 1) {
        prefix.shift();
        size = size / 1024;
    }
    return (Math.floor(size * 100) / 100.0).toFixed(2) + prefix.shift();
};

var formatTimeDelta = function (milliseconds) {
    var time = milliseconds;
    var prefix = ["ms", "s", "m", "h"];
    var div = [1000, 60, 60];
    while (time >= div[0] && prefix.length > 1) {
        prefix.shift();
        time = time / div.shift();
    }
    return Math.round(time) + prefix.shift();
};