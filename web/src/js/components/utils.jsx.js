//React utils. For other utilities, see ../utils.js

// http://blog.vjeux.com/2013/javascript/scroll-position-with-react.html (also contains inverse example)
var AutoScrollMixin = {
    componentWillUpdate: function () {
        var node = this.getDOMNode();
        this._shouldScrollBottom = (
            node.scrollTop !== 0 &&
            node.scrollTop + node.clientHeight === node.scrollHeight
        );
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


var Navigation = _.extend({}, ReactRouter.Navigation, {
    setQuery: function (dict) {
        var q = this.context.getCurrentQuery();
        for(var i in dict){
            if(dict.hasOwnProperty(i)){
                q[i] = dict[i] || undefined; //falsey values shall be removed.
            }
        }
        q._ = "_"; // workaround for https://github.com/rackt/react-router/pull/599
        this.replaceWith(this.context.getCurrentPath(), this.context.getCurrentParams(), q);
    },
    replaceWith: function(routeNameOrPath, params, query) {
        if(routeNameOrPath === undefined){
            routeNameOrPath = this.context.getCurrentPath();
        }
        if(params === undefined){
            params = this.context.getCurrentParams();
        }
        if(query === undefined){
            query = this.context.getCurrentQuery();
        }
        ReactRouter.Navigation.replaceWith.call(this, routeNameOrPath, params, query);
    }
});
_.extend(Navigation.contextTypes, ReactRouter.State.contextTypes);

var State = _.extend({}, ReactRouter.State, {
    getInitialState: function () {
        this._query = this.context.getCurrentQuery();
        this._queryWatches = [];
        return null;
    },
    onQueryChange: function (key, callback) {
        this._queryWatches.push({
            key: key,
            callback: callback
        });
    },
    componentWillReceiveProps: function (nextProps, nextState) {
        var q = this.context.getCurrentQuery();
        for (var i = 0; i < this._queryWatches.length; i++) {
            var watch = this._queryWatches[i];
            if (this._query[watch.key] !== q[watch.key]) {
                watch.callback(this._query[watch.key], q[watch.key], watch.key);
            }
        }
        this._query = q;
    }
});

var Splitter = React.createClass({
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
        this.getDOMNode().style.transform = "";
        window.removeEventListener("dragend", this.onDragEnd);
        window.removeEventListener("mouseup", this.onMouseUp);
        window.removeEventListener("mousemove", this.onMouseMove);
    },
    onMouseUp: function (e) {
        this.onDragEnd();

        var node = this.getDOMNode();
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
        this.getDOMNode().style.transform = "translate(" + dX + "px," + dY + "px)";
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
        var node = this.getDOMNode();
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