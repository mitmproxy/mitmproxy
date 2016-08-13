import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import ViewSelector from './ViewSelector'
import UploadContentButton from './UploadContentButton'
import DownloadContentButton from './DownloadContentButton'

ContentViewOptions.propTypes = {
    flow: React.PropTypes.object.isRequired,
    message: React.PropTypes.object.isRequired,
}

function ContentViewOptions(props) {
    const { flow, message, uploadContent, readonly, contentViewDescription } = props
    return (
        <div className="view-options">
            <ViewSelector message={message}/>
            &nbsp;
            <DownloadContentButton flow={flow} message={message}/>
            &nbsp;
            <UploadContentButton uploadContent={uploadContent}/>
            &nbsp;
            <span>{contentViewDescription}</span>
        </div>
    )
}

export default connect(
    state => ({
        contentViewDescription: state.ui.flow.viewDescription
    })
)(ContentViewOptions)
