import React, { Component, PropTypes } from 'react'
import FilterInput from './FilterInput'
import { Query } from '../../actions.js'
import {setInterceptPattern} from "../../ducks/settings"
import { connect } from 'react-redux'

class MainMenu extends Component {

    static title = 'Start'
    static route = 'flows'

    static propTypes = {
        settings: React.PropTypes.object.isRequired,
    }

    constructor(props, context) {
        super(props, context)
        this.onSearchChange = this.onSearchChange.bind(this)
        this.onHighlightChange = this.onHighlightChange.bind(this)
        this.onInterceptChange = this.onInterceptChange.bind(this)
    }

    onSearchChange(val) {
        this.props.updateLocation(undefined, { [Query.SEARCH]: val })
    }

    onHighlightChange(val) {
        this.props.updateLocation(undefined, { [Query.HIGHLIGHT]: val })
    }

    onInterceptChange(val) {
        this.props.setInterceptPattern(val);
    }

    render() {
        const { query, settings } = this.props

        const search = query[Query.SEARCH] || ''
        const highlight = query[Query.HIGHLIGHT] || ''
        const intercept = settings.intercept || ''

        return (
            <div>
                <div className="menu-row">
                    <FilterInput
                        ref="search"
                        placeholder="Search"
                        type="search"
                        color="black"
                        value={search}
                        onChange={this.onSearchChange}
                    />
                    <FilterInput
                        ref="highlight"
                        placeholder="Highlight"
                        type="tag"
                        color="hsl(48, 100%, 50%)"
                        value={highlight}
                        onChange={this.onHighlightChange}
                    />
                    <FilterInput
                        ref="intercept"
                        placeholder="Intercept"
                        type="pause"
                        color="hsl(208, 56%, 53%)"
                        value={intercept}
                        onChange={this.onInterceptChange}
                    />
                </div>
                <div className="clearfix"></div>
            </div>
        )
    }
}

export default connect(undefined, {
    setInterceptPattern
})(MainMenu);
