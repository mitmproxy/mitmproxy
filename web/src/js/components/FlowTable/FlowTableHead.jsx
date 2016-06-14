import React, { PropTypes } from 'react'
import { bindActionCreators } from 'redux'
import { connect } from 'react-redux'
import classnames from 'classnames'
import columns from './FlowColumns'

import { setSort } from "../../ducks/flows"

FlowTableHead.propTypes = {
    onSort: PropTypes.func.isRequired,
    sortDesc: React.PropTypes.bool.isRequired,
    sortColumn: React.PropTypes.string,
}

function FlowTableHead({ sortColumn, sortDesc, onSort }) {
    const sortType = sortDesc ? 'sort-desc' : 'sort-asc'

    return (
        <tr>
            {columns.map(Column => (
                <th className={classnames(Column.headerClass, sortColumn === Column.name && sortType)}
                    key={Column.name}
                    onClick={() => onClick(Column)}>
                    {Column.headerName}
                </th>
            ))}
        </tr>
    )

    function onClick(Column) {
        onSort({ sortColumn: Column.name, sortDesc: Column.name !== sortColumn ? false : !sortDesc })
    }
}

export default connect(
    state => ({
        sortDesc: state.flows.sort.sortDesc,
        sortColumn: state.flows.sort.sortColumn,
    }),
    dispatch => bindActionCreators({
        onSort: setSort,
    }, dispatch)
)(FlowTableHead)
