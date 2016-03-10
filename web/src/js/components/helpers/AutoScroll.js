import React from "react";
import ReactDOM from "react-dom";

const symShouldStick = Symbol("shouldStick");
const isAtBottom = v => v.scrollTop + v.clientHeight === v.scrollHeight;

export default Component => Object.assign(class AutoScrollWrapper extends Component {

    static displayName = Component.name;

    componentWillUpdate() {
        const viewport = ReactDOM.findDOMNode(this);
        this[symShouldStick] = viewport.scrollTop && isAtBottom(viewport);
        super.componentWillUpdate && super.componentWillUpdate();
    }

    componentDidUpdate() {
        const viewport = ReactDOM.findDOMNode(this);
        if (this[symShouldStick] && !isAtBottom(viewport)) {
            viewport.scrollTop = viewport.scrollHeight;
        }
        super.componentDidUpdate && super.componentDidUpdate();
    }

}, Component);
