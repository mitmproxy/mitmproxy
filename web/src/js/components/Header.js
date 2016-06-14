import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import classnames from 'classnames'
import { toggleEventLogVisibility } from '../ducks/eventLog'
import MainMenu from './Header/MainMenu'
import ViewMenu from './Header/ViewMenu'
import OptionMenu from './Header/OptionMenu'
import FileMenu from './Header/FileMenu'
import FlowMenu from './Header/FlowMenu'
import {setActiveMenu} from '../ducks/view'

class Header extends Component {

    static entries = [MainMenu, ViewMenu, OptionMenu, FlowMenu]

    static propTypes = {
        settings: PropTypes.object.isRequired,
    }

    handleClick(active, e) {
        e.preventDefault()
        this.props.setActiveMenu(active.title)
       // this.props.updateLocation(active.route)
       // this.setState({ active })
    }

    render() {
        const { settings, updateLocation, query, selectedFlow, active_menu} = this.props
        const Active = _.find(Header.entries, (e) => e.title == active_menu);
        const entries = selectedFlow ? Header.entries : Header.entries.filter((h) => h != FlowMenu)
        return (
            <header>
                <nav className="nav-tabs nav-tabs-lg">
                    <FileMenu/>
                    {entries.map(Entry => (
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
export default connect(
    (state) => ({
        selectedFlow: state.flows.selected[0],
        active_menu: state.view.active_menu
    }),
    dispatch => bindActionCreators({
        setActiveMenu,
    }, dispatch)
)(Header)
