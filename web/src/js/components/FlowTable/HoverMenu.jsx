import React, { Component } from 'react'
import { connect } from 'react-redux'
import { update as updateSettings } from "../../ducks/settings"
import Dropdown from '../common/Dropdown'

class HoverMenu extends Component {
    constructor(props, context) {
        super(props, context)
    }

    onClick(e, example) {
        e.preventDefault();
        let intercept = this.props.intercept
        if (intercept && intercept.includes(example)) {
            return
        }
        if (!intercept) {
            intercept = example
        } else {
            intercept = `${intercept} | ${example}`
        }
        this.props.updateSettings({ intercept })
    }

    render() {
        const { flow } = this.props
        if (!flow) {
            return null
        }
        return (
            <Dropdown className="pull-left btn btn-default" btnClass="special" icon="fa-ellipsis-v" text="Actions">
                <a href="#" onClick={(e) =>{
                    this.onClick(e, flow.request.host)
                }}>
                    <i className="fa fa-fw fa-plus"></i>
                    &nbsp;Intercept {flow.request.host}
                </a>
                { flow.request.path != "/" ? <a href="#" onClick={(e) =>{
                    this.onClick(e, flow.request.host + flow.request.path)
                }}>
                    <i className="fa fa-fw fa-plus"></i>
                    &nbsp;Intercept {flow.request.host + flow.request.path}
                </a> : null }
                <a href="#" onClick={(e) =>{
                    this.onClick(e,  `~m POST & ${flow.request.host}`)
                }}>
                    <i className="fa fa-fw fa-plus"></i>
                    &nbsp;Intercept all POST requests from this host
                </a>
            </Dropdown>
        )
    }
}

export default connect(
    state => ({
        flow: state.flows.byId[state.flows.selected[0]],
        intercept: state.settings.intercept,
    }),
    {
        updateSettings,
    }
)(HoverMenu)