import React, { PropTypes } from 'react'
import classnames from 'classnames'
import views, { ViewAuto } from './ContentViews'

ViewSelector.propTypes = {
    active: PropTypes.func.isRequired,
    message: PropTypes.object.isRequired,
    onSelectView: PropTypes.func.isRequired,
}

export default function ViewSelector({ active, message, onSelectView }) {
    return (
        <div className="view-selector btn-group btn-group-xs">
            {views.map(View => (
                <button
                    key={View.name}
                    onClick={() => onSelectView(View)}
                    className={classnames('btn btn-default', { active: View === active })}>
                    {View === ViewAuto ? (
                        `auto: ${ViewAuto.findView(message).name.toLowerCase().replace('view', '')}`
                    ) : (
                        View.name.toLowerCase().replace('view', '')
                    )}
                </button>
            ))}
        </div>
    )
}
