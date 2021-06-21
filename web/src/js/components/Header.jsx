import React, { Component } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import classnames from 'classnames'
import MainMenu from './Header/MainMenu'
import OptionMenu from './Header/OptionMenu'
import FileMenu from './Header/FileMenu'
import FlowMenu from './Header/FlowMenu'
import {setActiveMenu} from '../ducks/ui/header'
import ConnectionIndicator from "./Header/ConnectionIndicator"
import HideInStatic from './common/HideInStatic'

class Header extends Component {
    static entries = [MainMenu, OptionMenu]

    handleClick(active, e) {
        e.preventDefault()
        this.props.setActiveMenu(active.title)
    }

    render() {
        const { selectedFlowId, activeMenu} = this.props

        let entries = [...Header.entries]
        if(selectedFlowId)
            entries.push(FlowMenu)

        // Make sure to have a fallback in case FlowMenu is selected but we don't have any flows
        // (e.g. because they are all deleted or not yet received)
        const Active = _.find(entries, (e) => e.title == activeMenu) || MainMenu

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
                    <HideInStatic>
                        <ConnectionIndicator/>
                    </HideInStatic>
                </nav>
                <div>
                    <Active/>
                </div>
            </header>
        )
    }
}

export default connect(
    state => ({
        selectedFlowId: state.flows.selected[0],
        activeMenu: state.ui.header.activeMenu,
    }),
    {
        setActiveMenu,
    }
)(Header)
