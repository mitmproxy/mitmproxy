import React from 'react'
import { MessageUtils } from "../../flow/utils"

type DownloadContentButtonProps = {
    flow: object,
    message: object,
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
