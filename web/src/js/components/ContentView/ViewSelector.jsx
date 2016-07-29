import React, { PropTypes } from 'react'
import classnames from 'classnames'
import { connect } from 'react-redux'
import * as ContentViews from './ContentViews'
import { setContentView } from "../../ducks/ui/flow";


function ViewButton({ name, setContentView, children, activeView }) {
    return (
        <button
            onClick={() => setContentView(name)}
            className={classnames('btn btn-default', { active: name === activeView })}>
            {children}
        </button>
    )
}
ViewButton = connect(state => ({
    activeView: state.ui.flow.contentView
}), {
    setContentView
})(ViewButton)


ViewSelector.propTypes = {
    message: PropTypes.object.isRequired,
}
function ViewSelector({contentViews, isEdit }) {
    let edit = ContentViews.Edit.displayName
    return (
        <div className="view-selector btn-group btn-group-xs">

            {contentViews.map(name =>
                <ViewButton key={name} name={name}>{name.toLowerCase().replace('_', ' ')}</ViewButton>
            )}

            {isEdit &&
                <ViewButton key={edit} name={edit}>{edit.toLowerCase()}</ViewButton>
            }

        </div>
    )
}

export default connect (
    state => ({
        contentViews: state.settings.contentViews,
        isEdit: !!state.ui.flow.modifiedFlow,
    }))(ViewSelector)
