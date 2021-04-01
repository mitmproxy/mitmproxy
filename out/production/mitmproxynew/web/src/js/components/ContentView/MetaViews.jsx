import React from 'react'
import { formatSize } from '../../utils.js'
import UploadContentButton from './UploadContentButton'
import DownloadContentButton from './DownloadContentButton'

export function ContentEmpty({ flow, message }) {
    return (
        <div className="alert alert-info">
            No {flow.request === message ? 'request' : 'response'} content.
        </div>
    )
}

export function ContentMissing({ flow, message }) {
    return (
        <div className="alert alert-info">
            {flow.request === message ? 'Request' : 'Response'} content missing.
        </div>
    )
}

export function ContentTooLarge({ message, onClick, uploadContent, flow }) {
    return (
        <div>
            <div className="alert alert-warning">

                <button onClick={onClick} className="btn btn-xs btn-warning pull-right">Display anyway</button>
                {formatSize(message.contentLength)} content size.
            </div>
            <div className="view-options text-center">
                <UploadContentButton uploadContent={uploadContent}/>
                &nbsp;
                <DownloadContentButton flow={flow} message={message}/>
            </div>
        </div>
    )
}
