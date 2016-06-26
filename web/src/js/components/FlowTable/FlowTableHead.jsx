import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import classnames from 'classnames'
import columns from './FlowColumns'

import { updateSort } from '../../ducks/views/main'

FlowTableHead.propTypes = {
    updateSort: PropTypes.func.isRequired,
    sortDesc: React.PropTypes.bool.isRequired,
    sortColumn: React.PropTypes.string,
}

function FlowTableHead({ sortColumn, sortDesc, updateSort }) {
    const sortType = sortDesc ? 'sort-desc' : 'sort-asc'

    return (
        <tr>
            {columns.map(Column => (
                <th className={classnames(Column.headerClass, sortColumn === Column.name && sortType)}
                    key={Column.name}
                    onClick={() => updateSort(Column.name, Column.name !== sortColumn ? false : !sortDesc)}>
                    {Column.headerName}
                </th>
            ))}
        </tr>
    )
}

export default connect(
    state => ({
        sortDesc: state.flows.views.main.sort.desc,
        sortColumn: state.flows.views.main.sort.column,
    }),
    {
        updateSort
    }
)(FlowTableHead)
