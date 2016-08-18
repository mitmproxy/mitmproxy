import React, { PropTypes, Component } from 'react'
import { connect } from 'react-redux'
import * as ContentViews from './ContentViews'
import { setContentView } from '../../ducks/ui/flow';
import Dropdown from '../common/Dropdown'


ViewSelector.propTypes = {
    contentViews: PropTypes.array.isRequired,
    activeView: PropTypes.string.isRequired,
    isEdit: PropTypes.bool.isRequired,
    setContentView: PropTypes.func.isRequired
}

function ViewSelector ({contentViews, activeView, isEdit, setContentView}){
    let edit = ContentViews.Edit.displayName
    let inner = <span> <b>View:</b> {activeView}<span className="caret"></span> </span>

    return (
        <Dropdown dropup className="pull-left" btnClass="btn btn-default btn-xs" text={inner}>
            {contentViews.map(name =>
                <a href="#" key={name} onClick={e => {e.preventDefault(); setContentView(name)}}>
                    {name.toLowerCase().replace('_', ' ')}
                </a>
                )
            }
            {isEdit &&
                <a href="#" onClick={e => {e.preventDefault(); setContentView(edit)}}>
                    {edit.toLowerCase()}
                </a>
            }
        </Dropdown>
    )
}

export default connect (
    state => ({
        contentViews: state.settings.contentViews,
        activeView: state.ui.flow.contentView,
        isEdit: !!state.ui.flow.modifiedFlow,
    }), {
        setContentView,
    }
)(ViewSelector)
