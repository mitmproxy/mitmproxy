import React, { Component, useCallback } from 'react'
import { connect } from 'react-redux'
import { update as updateSettings } from "../../ducks/settings"
import Dropdown from '../common/Dropdown'
import DropdownSubMenu from '../common/DropdownSubMenu'

let SubMenu = ({flow, intercept, updateSettings}) => {
    const onClick = useCallback((e, example) => {
        e.preventDefault();
        if (intercept && intercept.includes(example)) {
            return
        }
        if (!intercept) {
            intercept = example
        } else {
            intercept = `${intercept} | ${example}`
        }
        updateSettings({ intercept })
    }, [intercept])

    return (
        <DropdownSubMenu text="Intercept requests like this">
            <a href="#" onClick={(e) =>{
                onClick(e, flow.request.host)
            }}>
                <i className="fa fa-fw fa-plus"></i>
                &nbsp;Intercept {flow.request.host}
            </a>
            { flow.request.path != "/" ? <a href="#" onClick={(e) =>{
                onClick(e, flow.request.host + flow.request.path)
            }}>
                <i className="fa fa-fw fa-plus"></i>
                &nbsp;Intercept {flow.request.host + flow.request.path}
            </a> : null }
            <a href="#" onClick={(e) =>{
                onClick(e,  `~m POST & ${flow.request.host}`)
            }}>
                <i className="fa fa-fw fa-plus"></i>
                &nbsp;Intercept all POST requests from this host
            </a>
        </DropdownSubMenu>
    )
}

SubMenu = connect(
    state => ({
        flow: state.flows.byId[state.flows.selected[0]],
        intercept: state.settings.intercept,
    }),
    {
        updateSettings,
    }
)(SubMenu)

class HoverMenu extends Component {
    constructor(props, context) {
        super(props, context)
    }

    render() {
        const { flow } = this.props
        if (!flow) {
            return null
        }
        return (
            <Dropdown className="pull-right" btnClass="special" icon="fa fa-fw fa-ellipsis-h" submenu={<SubMenu />}>
                <a href="#" onClick={(e) =>{
                    e.preventDefault()
                }}>
                    <i className="fa fa-fw fa-plus"></i>
                    &nbsp;Copy as Curl
                </a>
                <a href="#" onClick={(e) =>{
                    e.preventDefault()
                }}>
                    <i className="fa fa-fw fa-plus"></i>
                    &nbsp;Download HAR
                </a>
            </Dropdown>
        )
    }
}

export default connect(
    state => ({
        flow: state.flows.byId[state.flows.selected[0]],
    }),
    null
)(HoverMenu)