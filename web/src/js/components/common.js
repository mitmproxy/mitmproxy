import React from "react"
import ReactDOM from "react-dom"
import _ from "lodash"
import {Key} from "../utils.js";


export var Router = {
    contextTypes: {
        location: React.PropTypes.object,
        router: React.PropTypes.object.isRequired
    },
    updateLocation: function (pathname, queryUpdate) {
        if (pathname === undefined) {
            pathname = this.context.location.pathname;
        }
        var query = this.context.location.query;
        if (queryUpdate !== undefined) {
            for (var i in queryUpdate) {
                if (queryUpdate.hasOwnProperty(i)) {
                    query[i] = queryUpdate[i] || undefined; //falsey values shall be removed.
                }
            }
        }
        this.context.router.replace({pathname, query});
    },
    getQuery: function () {
        // For whatever reason, react-router always returns the same object, which makes comparing
        // the current props with nextProps impossible. As a workaround, we just clone the query object.
        return _.clone(this.context.location.query);
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

export const ToggleButton = (props) =>
    <div className="input-group toggle-btn">
        <div
        className={"btn " + (props.checked ? "btn-primary" : "btn-default")}
        onClick={props.onToggleChanged}>
        <span className={"fa " + (props.checked ? "fa-check-square-o" : "fa-square-o")}>&nbsp;{props.name}</span>
        </div>
    </div>;

ToggleButton.propTypes = {
    name: React.PropTypes.string.isRequired,
    onToggleChanged: React.PropTypes.func.isRequired
};

export class ToggleInputButton extends React.Component {
    constructor(props) {
        super(props);
        this.state = {txt: props.txt};
    }

    render() {
        return (
            <div className="input-group toggle-input-btn">
                <span
                    className="input-group-btn"
                    onClick={() => this.props.onToggleChanged(this.state.txt)}>
                    <div className={"btn  " + (this.props.checked ? "btn-primary" : "btn-default")}>
                        <span className={"fa " + (this.props.checked ? "fa-check-square-o" : "fa-square-o")}/>
                        &nbsp;{this.props.name}
                    </div>
                </span>
                <input
                    className="form-control"
                    placeholder={this.props.placeholder}
                    disabled={this.props.checked}
                    value={this.state.txt}
                    onChange={e => this.setState({txt: e.target.value})}
                    onKeyDown={e => {if (e.keyCode === Key.ENTER) this.props.onToggleChanged(this.state.txt); e.stopPropagation()}}/>
            </div>
        );
    }
};
ToggleInputButton.propTypes = {
    name: React.PropTypes.string.isRequired,
    txt: React.PropTypes.string.isRequired,
    onToggleChanged: React.PropTypes.func.isRequired
};



