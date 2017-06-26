import React, { Component } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { toggleFilter, toggleVisibility } from '../ducks/eventLog'
import ToggleButton from './common/ToggleButton'
import EventList from './EventLog/EventList'

export class PureEventLog extends Component {

    static propTypes = {
        filters: PropTypes.object.isRequired,
        events: PropTypes.array.isRequired,
        toggleFilter: PropTypes.func.isRequired,
        close: PropTypes.func.isRequired,
        defaultHeight: PropTypes.number,
    }

    static defaultProps = {
        defaultHeight: 200,
    }

    constructor(props, context) {
        super(props, context)

        this.state = { height: this.props.defaultHeight }

        this.onDragStart = this.onDragStart.bind(this)
        this.onDragMove = this.onDragMove.bind(this)
        this.onDragStop = this.onDragStop.bind(this)
    }

    onDragStart(event) {
        event.preventDefault()
        this.dragStart = this.state.height + event.pageY
        window.addEventListener('mousemove', this.onDragMove)
        window.addEventListener('mouseup', this.onDragStop)
        window.addEventListener('dragend', this.onDragStop)
    }

    onDragMove(event) {
        event.preventDefault()
        this.setState({ height: this.dragStart - event.pageY })
    }

    onDragStop(event) {
        event.preventDefault()
        window.removeEventListener('mousemove', this.onDragMove)
    }

    render() {
        const { height } = this.state
        const { filters, events, toggleFilter, close } = this.props

        return (
            <div className="eventlog" style={{ height }}>
                <div onMouseDown={this.onDragStart}>
                    Eventlog
                    <div className="pull-right">
                        {['debug', 'info', 'web', 'warn', 'error'].map(type => (
                            <ToggleButton key={type} text={type} checked={filters[type]} onToggle={() => toggleFilter(type)}/>
                        ))}
                        <i onClick={close} className="fa fa-close"></i>
                    </div>
                </div>
                <EventList events={events} />
            </div>
        )
    }
}

export default connect(
    state => ({
        filters: state.eventLog.filters,
        events: state.eventLog.view,
    }),
    {
        close: toggleVisibility,
        toggleFilter: toggleFilter,
    }
)(PureEventLog)
