import PropTypes from "prop-types"

DocsLink.propTypes = {
    resource: PropTypes.string.isRequired,
}

export default function DocsLink({ children, resource }) {
    let url = `http://docs.mitmproxy.org/en/stable/${resource}`
    return (
        <a target="_blank" href={url}>
            {children || <i className="fa fa-question-circle"></i>}
        </a>
    )
}
