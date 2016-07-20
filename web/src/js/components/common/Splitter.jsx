import React, { Component } from 'react'
import ReactDOM from 'react-dom'
import classnames from 'classnames'

export default class Splitter extends Component {

    static defaultProps = { axis: 'x' }

    constructor(props, context) {
        super(props, context)

        this.state = { applied: false, startX: false, startY: false }

        this.onMouseMove = this.onMouseMove.bind(this)
        this.onMouseDown = this.onMouseDown.bind(this)
        this.onMouseUp = this.onMouseUp.bind(this)
        this.onDragEnd = this.onDragEnd.bind(this)
    }

    onMouseDown(e) {
        this.setState({ startX: e.pageX, startY: e.pageY })

        window.addEventListener('mousemove', this.onMouseMove)
        window.addEventListener('mouseup', this.onMouseUp)
        // Occasionally, only a dragEnd event is triggered, but no mouseUp.
        window.addEventListener('dragend', this.onDragEnd)
    }

    onDragEnd() {
        ReactDOM.findDOMNode(this).style.transform = ''

        window.removeEventListener('dragend', this.onDragEnd)
        window.removeEventListener('mouseup', this.onMouseUp)
        window.removeEventListener('mousemove', this.onMouseMove)
    }

    onMouseUp(e) {
        this.onDragEnd()

        const node = ReactDOM.findDOMNode(this)
        const prev = node.previousElementSibling

        let flexBasis = prev.offsetHeight + e.pageY - this.state.startY

        if (this.props.axis === 'x') {
            flexBasis = prev.offsetWidth + e.pageX - this.state.startX
        }

        prev.style.flex = `0 0 ${Math.max(0, flexBasis)}px`
        node.nextElementSibling.style.flex = '1 1 auto'

        this.setState({ applied: true })
        this.onResize()
    }

    onMouseMove(e) {
        let dX = 0
        let dY = 0
        if (this.props.axis === 'x') {
            dX = e.pageX - this.state.startX
        } else {
            dY = e.pageY - this.state.startY
        }
        ReactDOM.findDOMNode(this).style.transform = `translate(${dX}px, ${dY}px)`
    }

    onResize() {
        // Trigger a global resize event. This notifies components that employ virtual scrolling
        // that their viewport may have changed.
        window.setTimeout(() => window.dispatchEvent(new CustomEvent('resize')), 1)
    }

    reset(willUnmount) {
        if (!this.state.applied) {
            return
        }

        const node = ReactDOM.findDOMNode(this)

        node.previousElementSibling.style.flex = ''
        node.nextElementSibling.style.flex = ''

        if (!willUnmount) {
            this.setState({ applied: false })
        }
        this.onResize()
    }

    componentWillUnmount() {
        this.reset(true)
    }

    render() {
        return (
            <div className={classnames('splitter', this.props.axis === 'x' ? 'splitter-x' : 'splitter-y')}>
                <div onMouseDown={this.onMouseDown} draggable="true"></div>
            </div>
        )
    }
}
