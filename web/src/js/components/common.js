var React = require("react");
var ReactDOM = require("react-dom");
var ReactRouter = require("react-router");
var _ = require("lodash");

// http://blog.vjeux.com/2013/javascript/scroll-position-with-react.html (also contains inverse example)
export var AutoScrollMixin = {
    componentWillUpdate: function () {
        var node = ReactDOM.findDOMNode(this);
        this._shouldScrollBottom = (
        node.scrollTop !== 0 &&
        node.scrollTop + node.clientHeight === node.scrollHeight
        );
    },
    componentDidUpdate: function () {
        if (this._shouldScrollBottom) {
            var node = ReactDOM.findDOMNode(this);
            node.scrollTop = node.scrollHeight;
        }
    },
};


export var StickyHeadMixin = {
    adjustHead: function () {
        // Abusing CSS transforms to set the element
        // referenced as head into some kind of position:sticky.
        var head = this.refs.head;
        head.style.transform = "translate(0," + ReactDOM.findDOMNode(this).scrollTop + "px)";
    }
};

export var SettingsState = {
    contextTypes: {
        settingsStore: React.PropTypes.object.isRequired
    },
    getInitialState: function () {
        return {
            settings: this.context.settingsStore.dict
        };
    },
    componentDidMount: function () {
        this.context.settingsStore.addListener("recalculate", this.onSettingsChange);
    },
    componentWillUnmount: function () {
        this.context.settingsStore.removeListener("recalculate", this.onSettingsChange);
    },
    onSettingsChange: function () {
        this.setState({
            settings: this.context.settingsStore.dict
        });
    },
};


export var ChildFocus = {
    contextTypes: {
        returnFocus: React.PropTypes.func
    },
    returnFocus: function(){
        ReactDOM.findDOMNode(this).blur();
        window.getSelection().removeAllRanges();
        this.context.returnFocus();
    }
};


export var Navigation = {
    contextTypes: {
        routerFoo: React.PropTypes.object,
        router: React.PropTypes.object.isRequired
    },
    setQuery: function (dict) {
        var q = this.context.routerFoo.location.query;
        for (var i in dict) {
            if (dict.hasOwnProperty(i)) {
                q[i] = dict[i] || undefined; //falsey values shall be removed.
            }
        }
        this.replaceWith(undefined, q);
    },
    replaceWith: function (pathname, query) {
        if (pathname === undefined) {
            pathname = this.context.routerFoo.location.pathname;
        }
        if (query === undefined) {
            query = this.context.routerFoo.query;
        }
        console.log({ pathname, query });
        this.context.router.replace({ pathname, query });
    }
};

// react-router is fairly good at changing its API regularly.
// We keep the old method for now - if it should turn out that their changes are permanent,
// we may remove this mixin and access react-router directly again.
export var RouterState = {
    contextTypes: {
        routerFoo: React.PropTypes.object,
    },
    getQuery: function () {
        // For whatever reason, react-router always returns the same object, which makes comparing
        // the current props with nextProps impossible. As a workaround, we just clone the query object.
        return _.clone(this.context.routerFoo.location.query);
    },
    getParams: function () {
        return _.clone(this.context.routerFoo.params);
    }
};

export var Splitter = React.createClass({
    getDefaultProps: function () {
        return {
            axis: "x"
        };
    },
    getInitialState: function () {
        return {
            applied: false,
            startX: false,
            startY: false
        };
    },
    onMouseDown: function (e) {
        this.setState({
            startX: e.pageX,
            startY: e.pageY
        });
        window.addEventListener("mousemove", this.onMouseMove);
        window.addEventListener("mouseup", this.onMouseUp);
        // Occasionally, only a dragEnd event is triggered, but no mouseUp.
        window.addEventListener("dragend", this.onDragEnd);
    },
    onDragEnd: function () {
        ReactDOM.findDOMNode(this).style.transform = "";
        window.removeEventListener("dragend", this.onDragEnd);
        window.removeEventListener("mouseup", this.onMouseUp);
        window.removeEventListener("mousemove", this.onMouseMove);
    },
    onMouseUp: function (e) {
        this.onDragEnd();

        var node = ReactDOM.findDOMNode(this);
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;

        var dX = e.pageX - this.state.startX;
        var dY = e.pageY - this.state.startY;
        var flexBasis;
        if (this.props.axis === "x") {
            flexBasis = prev.offsetWidth + dX;
        } else {
            flexBasis = prev.offsetHeight + dY;
        }

        prev.style.flex = "0 0 " + Math.max(0, flexBasis) + "px";
        next.style.flex = "1 1 auto";

        this.setState({
            applied: true
        });
        this.onResize();
    },
    onMouseMove: function (e) {
        var dX = 0, dY = 0;
        if (this.props.axis === "x") {
            dX = e.pageX - this.state.startX;
        } else {
            dY = e.pageY - this.state.startY;
        }
        ReactDOM.findDOMNode(this).style.transform = "translate(" + dX + "px," + dY + "px)";
    },
    onResize: function () {
        // Trigger a global resize event. This notifies components that employ virtual scrolling
        // that their viewport may have changed.
        window.setTimeout(function () {
            window.dispatchEvent(new CustomEvent("resize"));
        }, 1);
    },
    reset: function (willUnmount) {
        if (!this.state.applied) {
            return;
        }
        var node = ReactDOM.findDOMNode(this);
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;

        prev.style.flex = "";
        next.style.flex = "";

        if (!willUnmount) {
            this.setState({
                applied: false
            });
        }
        this.onResize();
    },
    componentWillUnmount: function () {
        this.reset(true);
    },
    render: function () {
        var className = "splitter";
        if (this.props.axis === "x") {
            className += " splitter-x";
        } else {
            className += " splitter-y";
        }
        return (
            <div className={className}>
                <div onMouseDown={this.onMouseDown} draggable="true"></div>
            </div>
        );
    }
});