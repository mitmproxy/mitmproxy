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
function ViewSelector({ message, contentViews }) {

    let autoView = ContentViews.ViewAuto.findView(message)
    let autoViewName = (autoView.displayName || autoView.name)
        .toLowerCase()
        .replace('view', '')
        .replace(/ContentLoader\((.+)\)/,"$1")

    return (
        <div className="view-selector btn-group btn-group-xs">

            {Object.keys(ContentViews).map(name =>
                name === "ViewRaw"  &&
                <ViewButton key={name} name={name}>{name.toLowerCase().replace('view', '')}</ViewButton>
            )}

            {contentViews.map(name =>
                <ViewButton key={name} name={name}>{name.toLowerCase().replace('view', '')}</ViewButton>
            )}

        </div>
    )
}

export default connect (
    state => ({
        contentViews: state.settings.contentViews
    }))(ViewSelector)
