import React, { Component } from 'react'
import PropTypes from 'prop-types'
import ReactDOM from 'react-dom'
import shallowEqual from 'shallowequal'
import AutoScroll from '../helpers/AutoScroll'
import { calcVScroll } from '../helpers/VirtualScroll'

class EventLogList extends Component {

    static propTypes = {
        events: PropTypes.array.isRequired,
        rowHeight: PropTypes.number,
    }

    static defaultProps = {
        rowHeight: 18,
    }

    constructor(props) {
        super(props)

        this.heights = {}
        this.state = { vScroll: calcVScroll() }

        this.onViewportUpdate = this.onViewportUpdate.bind(this)
    }

    componentDidMount() {
        window.addEventListener('resize', this.onViewportUpdate)
        this.onViewportUpdate()
    }

    componentWillUnmount() {
        window.removeEventListener('resize', this.onViewportUpdate)
    }

    componentDidUpdate() {
        this.onViewportUpdate()
    }

    onViewportUpdate() {
        const viewport = ReactDOM.findDOMNode(this)

        const vScroll = calcVScroll({
            itemCount: this.props.events.length,
            rowHeight: this.props.rowHeight,
            viewportTop: viewport.scrollTop,
            viewportHeight: viewport.offsetHeight,
            itemHeights: this.props.events.map(entry => this.heights[entry.id]),
        })

        if (!shallowEqual(this.state.vScroll, vScroll)) {
            this.setState({vScroll})
        }
    }

    setHeight(id, node) {
        if (node && !this.heights[id]) {
            const height = node.offsetHeight
            if (this.heights[id] !== height) {
                this.heights[id] = height
                this.onViewportUpdate()
            }
        }
    }

    render() {
        const { vScroll } = this.state
        const { events } = this.props

        return (
            <pre onScroll={this.onViewportUpdate}>
                <div style={{ height: vScroll.paddingTop }}></div>
                {events.slice(vScroll.start, vScroll.end).map(event => (
                    <div key={event.id} ref={node => this.setHeight(event.id, node)}>
                        <LogIcon event={event}/>
                        {event.message}
                    </div>
                ))}
                <div style={{ height: vScroll.paddingBottom }}></div>
            </pre>
        )
    }
}

function LogIcon({ event }) {
    const icon = {
      web: 'html5',
      debug: 'bug',
      warn: 'exclamation-triangle',
      error: 'ban'
    }[event.level] || 'info'
    return <i className={`fa fa-fw fa-${icon}`}></i>
}

export default AutoScroll(EventLogList)
