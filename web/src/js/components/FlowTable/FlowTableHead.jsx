import React  from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import classnames from 'classnames'
import columns from './FlowColumns'

import { setSort } from '../../ducks/flows'

FlowTableHead.propTypes = {
    setSort: PropTypes.func.isRequired,
    sortDesc: PropTypes.bool.isRequired,
    sortColumn: PropTypes.string,
}

function FlowTableHead({ sortColumn, sortDesc, setSort }) {
    const sortType = sortDesc ? 'sort-desc' : 'sort-asc'

    return (
        <tr>
            {columns.map(Column => (
                <th className={classnames(Column.headerClass, sortColumn === Column.name && sortType)}
                    key={Column.name}
                    onClick={() => setSort(Column.name, Column.name !== sortColumn ? false : !sortDesc)}>
                    {Column.headerName}
                </th>
            ))}
        </tr>
    )
}

export default connect(
    state => ({
        sortDesc: state.flows.sort.desc,
        sortColumn: state.flows.sort.column,
    }),
    {
        setSort
    }
)(FlowTableHead)
