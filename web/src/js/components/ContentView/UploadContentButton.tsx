import React from 'react'
import FileChooser from '../common/FileChooser'

type UploadContentButtonProps = {
    uploadContent: () => any,
}

export default function UploadContentButton({ uploadContent }: UploadContentButtonProps) {

    return (
        <FileChooser
            icon="fa-upload"
            title="Upload a file to replace the content."
            onOpenFile={uploadContent}
            className="btn btn-default btn-xs"/>
    )
}

