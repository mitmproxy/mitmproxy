import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import FilterInput from './FilterInput'
import { Query } from '../../actions.js'
import { updateSettings } from '../../ducks/settings'

class MainMenu extends Component {

    static title = 'Start'
    static route = 'flows'

    static propTypes = {
        query: PropTypes.object.isRequired,
        settings: PropTypes.object.isRequired,
        updateLocation: PropTypes.func.isRequired,
        onSettingsChange: PropTypes.func.isRequired,
    }

    constructor(props, context) {
        super(props, context)
        this.onSearchChange = this.onSearchChange.bind(this)
        this.onHighlightChange = this.onHighlightChange.bind(this)
    }

    onSearchChange(val) {
        this.props.updateLocation(undefined, { [Query.SEARCH]: val })
    }

    onHighlightChange(val) {
        this.props.updateLocation(undefined, { [Query.HIGHLIGHT]: val })
    }

    render() {
        const { query, settings, onSettingsChange } = this.props

        return (
            <div>
                <div className="menu-row">
                    <FilterInput
                        ref="search"
                        placeholder="Search"
                        type="search"
                        color="black"
                        value={query[Query.SEARCH] || ''}
                        onChange={this.onSearchChange}
                    />
                    <FilterInput
                        ref="highlight"
                        placeholder="Highlight"
                        type="tag"
                        color="hsl(48, 100%, 50%)"
                        value={query[Query.HIGHLIGHT] || ''}
                        onChange={this.onHighlightChange}
                    />
                    <FilterInput
                        ref="intercept"
                        placeholder="Intercept"
                        type="pause"
                        color="hsl(208, 56%, 53%)"
                        value={settings.intercept || ''}
                        onChange={intercept => onSettingsChange({ intercept })}
                    />
                </div>
                <div className="clearfix"></div>
            </div>
        )
    }
}

export default connect(
    state => ({
        settings: state.settings.settings,
    }),
    {
        onSettingsChange: updateSettings,
    }
)(MainMenu);
