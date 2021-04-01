import React from "react"
import PropTypes from "prop-types"
import { connect } from "react-redux"
import { ConnectionState } from "../../ducks/connection"


ConnectionIndicator.propTypes = {
    state: PropTypes.symbol.isRequired,
    message: PropTypes.string,

}
export function ConnectionIndicator({ state, message }) {
    switch (state) {
        case ConnectionState.INIT:
            return <span className="connection-indicator init">connecting…</span>;
        case ConnectionState.FETCHING:
            return <span className="connection-indicator fetching">fetching data…</span>;
        case ConnectionState.ESTABLISHED:
            return <span className="connection-indicator established">connected</span>;
        case ConnectionState.ERROR:
            return <span className="connection-indicator error"
                         title={message}>connection lost</span>;
        case ConnectionState.OFFLINE:
            return <span className="connection-indicator offline">offline</span>;
    }
}

export default connect(
    state => state.connection,
)(ConnectionIndicator)
