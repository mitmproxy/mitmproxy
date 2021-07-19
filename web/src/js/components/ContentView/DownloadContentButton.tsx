import React from 'react'
import { MessageUtils } from "../../flow/utils"
import { Flow, HTTPMessage } from '../../flow'

type DownloadContentButtonProps = {
    flow: Flow,
    message: HTTPMessage,
}

export default function DownloadContentButton({ flow, message }: DownloadContentButtonProps) {

    return (
        <a className="btn btn-default btn-xs"
           href={MessageUtils.getContentURL(flow, message)}
           title="Download the content of the flow.">
            <i className="fa fa-download"/>
        </a>
    )
}
