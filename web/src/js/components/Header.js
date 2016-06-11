import React, { Component, PropTypes } from 'react'
import classnames from 'classnames'
import { toggleEventLogVisibility } from '../ducks/eventLog'
import MainMenu from './Header/MainMenu'
import ViewMenu from './Header/ViewMenu'
import OptionMenu from './Header/OptionMenu'
import FileMenu from './Header/FileMenu'

export default class Header extends Component {

    static entries = [MainMenu, ViewMenu, OptionMenu]

    static propTypes = {
        settings: PropTypes.object.isRequired,
    }

    constructor(props, context) {
        super(props, context)
        this.state = { active: Header.entries[0] }
    }

    handleClick(active, e) {
        e.preventDefault()
        this.props.updateLocation(active.route)
        this.setState({ active })
    }

    render() {
        const { active: Active } = this.state
        const { settings, updateLocation, query } = this.props

        return (
            <header>
                <nav className="nav-tabs nav-tabs-lg">
                    <FileMenu/>
                    {Header.entries.map(Entry => (
                        <a key={Entry.title}
                           href="#"
                           className={classnames({ active: Entry === Active })}
                           onClick={e => this.handleClick(Entry, e)}>
                            {Entry.title}
                        </a>
                    ))}
                </nav>
                <div className="menu">
                    <Active
                        ref="active"
                        settings={settings}
                        updateLocation={updateLocation}
                        query={query}
                    />
                </div>
            </header>
        )
    }
}
