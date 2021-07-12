import React from "react";
import ReactDOM from "react-dom";

const symShouldStick = Symbol("shouldStick");
const isAtBottom = v => v.scrollTop + v.clientHeight === v.scrollHeight;

export default Component => Object.assign(class AutoScrollWrapper extends Component {

    static displayName = Component.name;

    UNSAFE_componentWillUpdate() {
        const viewport = ReactDOM.findDOMNode(this);
        this[symShouldStick] = viewport.scrollTop && isAtBottom(viewport);
        super.UNSAFE_componentWillUpdate && super.UNSAFE_componentWillUpdate();
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
