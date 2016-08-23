import { PropTypes } from 'react'
import FileChooser from '../common/FileChooser'

UploadContentButton.propTypes = {
    uploadContent: PropTypes.func.isRequired,
}

export default function UploadContentButton({ uploadContent }) {
    
    return (
        <FileChooser
            icon="fa-upload"
            title="Upload a file to replace the content."
            onOpenFile={uploadContent}
            className="btn btn-default btn-xs"/>
    )
}

