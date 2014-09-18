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
    adjustHead: function(){
        // Abusing CSS transforms to set the element
        // referenced as head into some kind of position:sticky.
        var head = this.refs.head.getDOMNode();
        head.style.transform = "translate(0,"+this.getDOMNode().scrollTop+"px)";
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
    ESC: 27
};