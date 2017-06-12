import React from 'react'
import { MessageUtils } from "../../flow/utils"
import PropTypes from 'prop-types'

DownloadContentButton.propTypes = {
    flow: PropTypes.object.isRequired,
    message: PropTypes.object.isRequired,
}

export default function DownloadContentButton({ flow, message }) {

    return (
        <a className="btn btn-default btn-xs"
           href={MessageUtils.getContentURL(flow, message)}
           title="Download the content of the flow.">
            <i className="fa fa-download"/>
        </a>
    )
}
