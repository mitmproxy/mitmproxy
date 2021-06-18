import React from 'react'
import PropTypes from 'prop-types'
import classnames from 'classnames'
import {defaultColumnNames} from './FlowColumns'
import { pure } from '../../utils'
import {getDisplayColumns} from './FlowTableHead'
import { connect } from 'react-redux'
import { update as updateSettings } from "../../ducks/settings"
import * as flowsActions from "../../ducks/flows"

FlowRow.propTypes = {
    onSelect: PropTypes.func.isRequired,
    flow: PropTypes.object.isRequired,
    highlighted: PropTypes.bool,
    selected: PropTypes.bool,
}

function FlowRow({ flow, selected, highlighted, onSelect, displayColumnNames, intercept, updateSettings, removeFlow }) {
    const className = classnames({
        'selected': selected,
        'highlighted': highlighted,
        'intercepted': flow.intercepted,
        'has-request': flow.request,
        'has-response': flow.response,
    })

    const displayColumns = getDisplayColumns(displayColumnNames)

    return (
        <tr className={className} onClick={() => onSelect(flow.id)}>
            {displayColumns.map(Column => (
                <Column key={Column.name} flow={flow} intercept={intercept} updateSettings={updateSettings} removeFlow={removeFlow} />
            ))}
        </tr>
    )
}

export default connect(
    state => ({
        displayColumnNames: state.options["web_columns"] ? state.options["web_columns"].value : defaultColumnNames,
        intercept: state.settings.intercept,
    }),
    {
        updateSettings,
        removeFlow: flowsActions.remove,
    }
)(pure(FlowRow))
