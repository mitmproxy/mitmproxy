import React, { PropTypes } from 'react'
import classnames from 'classnames'
import columns from './FlowColumns'
import { pure } from '../../utils'

FlowRow.propTypes = {
    onSelect: PropTypes.func.isRequired,
    onContextMenu: PropTypes.func.isRequired,
    flow: PropTypes.object.isRequired,
    highlighted: PropTypes.bool,
    selected: PropTypes.bool,
}

function FlowRow({ flow, selected, highlighted, onSelect, onContextMenu }) {
    const className = classnames({
        'selected': selected,
        'highlighted': highlighted,
        'intercepted': flow.intercepted,
        'has-request': flow.request,
        'has-response': flow.response,
    })

    return (
        <tr className={className} onClick={onSelect} onContextMenu={onContextMenu}>
            {columns.map(Column => (
                <Column key={Column.name} flow={flow}/>
            ))}
        </tr>
    )
}

export default pure(FlowRow)
