import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import classnames from 'classnames'
import { toggleEventLogVisibility } from '../ducks/eventLog'
import MainMenu from './Header/MainMenu'
import ViewMenu from './Header/ViewMenu'
import OptionMenu from './Header/OptionMenu'
import FileMenu from './Header/FileMenu'
import FlowMenu from './Header/FlowMenu'
import {setActiveMenu} from '../ducks/ui.js'

class Header extends Component {
    static entries = [MainMenu, ViewMenu, OptionMenu]

    handleClick(active, e) {
        e.preventDefault()
        this.props.setActiveMenu(active.title)
       // this.props.updateLocation(active.route)
       // this.setState({ active })
    }

    render() {
        const { updateLocation, query, selectedFlow, activeMenu} = this.props

        let entries = [...Header.entries]
        if(selectedFlow)
            entries.push(FlowMenu)

        const Active = _.find(entries, (e) => e.title == activeMenu)

        return (
            <header>
                <nav className="nav-tabs nav-tabs-lg">
                    <FileMenu/>
                    {entries.map(Entry => (
                        <a key={Entry.title}
                           href="#"
                           className={classnames({ active: Entry === Active})}
                           onClick={e => this.handleClick(Entry, e)}>
                            {Entry.title}
                        </a>
                    ))}
                </nav>
                <div className="menu">
                    <Active
                        updateLocation={updateLocation}
                        query={query}
                    />
                </div>
            </header>
        )
    }
}
export default connect(
    (state) => ({
        selectedFlow: state.flows.selected[0],
        activeMenu: state.ui.activeMenu
    }),
    {
        setActiveMenu,
    }
)(Header)
