import React, { PropTypes } from 'react'
import classnames from 'classnames'
import columns from './FlowColumns'
import { pure } from '../../utils'

FlowRow.propTypes = {
    onSelect: PropTypes.func.isRequired,
    flow: PropTypes.object.isRequired,
    highlighted: PropTypes.bool,
    selected: PropTypes.bool,
}

function FlowRow({ flow, selected, highlighted, onSelect }) {
    const className = classnames({
        'selected': selected,
        'highlighted': highlighted,
        'intercepted': flow.intercepted,
        'has-request': flow.request,
        'has-response': flow.response,
    })

    return (
        <tr className={className} onClick={event => onSelect(flow.id, event.ctrlKey, event.shiftKey)}>
            {columns.map(Column => (
                <Column key={Column.name} flow={flow}/>
            ))}
        </tr>
    )
}

export default pure(FlowRow)
