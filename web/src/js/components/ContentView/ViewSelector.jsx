import React from 'react'
import PropTypes from 'prop-types'
import {connect} from 'react-redux'
import {setContentView} from '../../ducks/ui/flow';
import Dropdown, {MenuItem} from '../common/Dropdown'


ViewSelector.propTypes = {
    contentViews: PropTypes.array.isRequired,
    activeView: PropTypes.string.isRequired,
    setContentView: PropTypes.func.isRequired
}

export function ViewSelector({contentViews, activeView, setContentView}) {
    let inner = <span><b>View:</b> {activeView.toLowerCase()} <span className="caret"/></span>

    return (
        <Dropdown
            text={inner}
            className="btn btn-default btn-xs pull-left"
            options={{placement:"top-start"}}>
            {contentViews.map(name =>
                <MenuItem key={name} onClick={() => setContentView(name)}>
                    {name.toLowerCase().replace('_', ' ')}
                </MenuItem>
            )}
        </Dropdown>
    )
}

export default connect(
    state => ({
        contentViews: state.settings.contentViews || [],
        activeView: state.ui.flow.contentView,
    }), {
        setContentView,
    }
)(ViewSelector)
