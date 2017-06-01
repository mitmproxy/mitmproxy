import React  from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import ViewSelector from './ViewSelector'
import UploadContentButton from './UploadContentButton'
import DownloadContentButton from './DownloadContentButton'

ContentViewOptions.propTypes = {
    flow: PropTypes.object.isRequired,
    message: PropTypes.object.isRequired,
}

function ContentViewOptions({ flow, message, uploadContent, readonly, contentViewDescription }) {
    return (
        <div className="view-options">
            {readonly ? <ViewSelector message={message}/> : <span><b>View:</b> edit</span>}
            &nbsp;
            <DownloadContentButton flow={flow} message={message}/>
            &nbsp;
            {!readonly && <UploadContentButton uploadContent={uploadContent}/> }
            &nbsp;
            {readonly && <span>{contentViewDescription}</span>}
        </div>
    )
}

export default connect(
    state => ({
        contentViewDescription: state.ui.flow.viewDescription,
        readonly: !state.ui.flow.modifiedFlow,
    })
)(ContentViewOptions)
