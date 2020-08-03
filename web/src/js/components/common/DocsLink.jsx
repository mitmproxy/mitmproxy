import React from "react"
import PropTypes from "prop-types"

DocsLink.propTypes = {
    resource: PropTypes.string.isRequired,
}

export default function DocsLink({ children, resource }) {
    let url = `https://docs.mitmproxy.org/stable/${resource}`
    return (
        <a target="_blank" href={url}>
            {children || <i className="fa fa-question-circle"></i>}
        </a>
    )
}
