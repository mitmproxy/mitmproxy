import React from 'react'
import PropTypes from 'prop-types'
import ReactDOM from 'react-dom'
import { connect } from 'react-redux'
import shallowEqual from 'shallowequal'
import AutoScroll from './helpers/AutoScroll'
import { calcVScroll } from './helpers/VirtualScroll'
import FlowTableHead from './FlowTable/FlowTableHead'
import FlowRow from './FlowTable/FlowRow'
import Filt from "../filt/filt"
import * as flowsActions from '../ducks/flows'


class FlowTable extends React.Component {

    static propTypes = {
        selectFlow: PropTypes.func.isRequired,
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

    UNSAFE_componentWillMount() {
        window.addEventListener('resize', this.onViewportUpdate)
    }

    UNSAFE_componentWillUnmount() {
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

    UNSAFE_componentWillReceiveProps(nextProps) {
        if (nextProps.selected && nextProps.selected !== this.props.selected) {
            this.shouldScrollIntoView = true
        }
    }

    onViewportUpdate() {
        const viewport = ReactDOM.findDOMNode(this)
        const viewportTop = viewport.scrollTop || 0

        const vScroll = calcVScroll({
            viewportTop,
            viewportHeight: viewport.offsetHeight || 0,
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
                        <tr style={{ height: vScroll.paddingTop }}/>
                        {flows.slice(vScroll.start, vScroll.end).map(flow => (
                            <FlowRow
                                key={flow.id}
                                flow={flow}
                                selected={flow === selected}
                                highlighted={isHighlighted(flow)}
                                onSelect={this.props.selectFlow}
                            />
                        ))}
                        <tr style={{ height: vScroll.paddingBottom }}/>
                    </tbody>
                </table>
            </div>
        )
    }
}

export const PureFlowTable = AutoScroll(FlowTable)

export default connect(
    state => ({
        flows: state.flows.view,
        highlight: state.flows.highlight,
        selected: state.flows.byId[state.flows.selected[0]],
    }),
    {
        selectFlow: flowsActions.select,
    }
)(PureFlowTable)
