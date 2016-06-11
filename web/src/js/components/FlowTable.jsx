import React, { PropTypes } from 'react'
import ReactDOM from 'react-dom'
import shallowEqual from 'shallowequal'
import AutoScroll from './helpers/AutoScroll'
import { calcVScroll } from './helpers/VirtualScroll'
import FlowTableHead from './FlowTable/FlowTableHead'
import FlowRow from './FlowTable/FlowRow'
import Filt from "../filt/filt"

class FlowTable extends React.Component {

    static propTypes = {
        onSelect: PropTypes.func.isRequired,
        flows: PropTypes.array.isRequired,
        rowHeight: PropTypes.number,
        highlight: PropTypes.string,
        selected: PropTypes.object,
    }

    static defaultProps = {
        rowHeight: 32,
    }

    constructor(props, context) {
        super(props, context)

        this.state = { vScroll: calcVScroll() }
        this.onViewportUpdate = this.onViewportUpdate.bind(this)
    }

    componentWillMount() {
        window.addEventListener('resize', this.onViewportUpdate)
    }

    componentWillUnmount() {
        window.removeEventListener('resize', this.onViewportUpdate)
    }

    componentDidUpdate() {
        this.onViewportUpdate()

        if (!this.shouldScrollIntoView) {
            return
        }

        this.shouldScrollIntoView = false

        const { rowHeight, flows, selected } = this.props
        const viewport = ReactDOM.findDOMNode(this)
        const head = ReactDOM.findDOMNode(this.refs.head)

        const headHeight = head ? head.offsetHeight : 0

        const rowTop = (flows.indexOf(selected) * rowHeight) + headHeight
        const rowBottom = rowTop + rowHeight

        const viewportTop = viewport.scrollTop
        const viewportHeight = viewport.offsetHeight

        // Account for pinned thead
        if (rowTop - headHeight < viewportTop) {
            viewport.scrollTop = rowTop - headHeight
        } else if (rowBottom > viewportTop + viewportHeight) {
            viewport.scrollTop = rowBottom - viewportHeight
        }
    }

    componentWillReceiveProps(nextProps) {
        if (nextProps.selected && nextProps.selected !== this.props.selected) {
            this.shouldScrollIntoView = true
        }
    }

    onViewportUpdate() {
        const viewport = ReactDOM.findDOMNode(this)
        const viewportTop = viewport.scrollTop

        const vScroll = calcVScroll({
            viewportTop,
            viewportHeight: viewport.offsetHeight,
            itemCount: this.props.flows.length,
            rowHeight: this.props.rowHeight,
        })

        if (this.state.viewportTop !== viewportTop || !shallowEqual(this.state.vScroll, vScroll)) {
            this.setState({ vScroll, viewportTop })
        }
    }

    render() {
        const { vScroll, viewportTop } = this.state
        const { flows, selected, highlight } = this.props
        const isHighlighted = highlight ? Filt.parse(highlight) : () => false

        return (
            <div className="flow-table" onScroll={this.onViewportUpdate}>
                <table>
                    <thead ref="head" style={{ transform: `translateY(${viewportTop}px)` }}>
                        <FlowTableHead />
                    </thead>
                    <tbody>
                        <tr style={{ height: vScroll.paddingTop }}></tr>
                        {flows.slice(vScroll.start, vScroll.end).map(flow => (
                            <FlowRow
                                key={flow.id}
                                flow={flow}
                                selected={flow === selected}
                                highlighted={isHighlighted(flow)}
                                onSelect={this.props.onSelect}
                            />
                        ))}
                        <tr style={{ height: vScroll.paddingBottom }}></tr>
                    </tbody>
                </table>
            </div>
        )
    }
}

export default AutoScroll(FlowTable)
