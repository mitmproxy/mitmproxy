import React, { Component } from 'react'
import _ from 'lodash'

import Nav from './FlowView/Nav'
import { Request, Response, Error } from './FlowView/Messages'
import Details from './FlowView/Details'
import Prompt from './Prompt'

export default class FlowView extends Component {

    static allTabs = { Request, Response, Error, Details }

    constructor(props, context) {
        super(props, context)

        this.state = { prompt: false }

        this.closePrompt = this.closePrompt.bind(this)
        this.selectTab = this.selectTab.bind(this)
    }

    getTabs() {
        return ['request', 'response', 'error'].filter(k => this.props.flow[k]).concat(['details'])
    }

    nextTab(increment) {
        const tabs = this.getTabs()
        // JS modulo operator doesn't correct negative numbers, make sure that we are positive.
        this.selectTab(tabs[(tabs.indexOf(this.props.tab) + increment + tabs.length) % tabs.length])
    }

    selectTab(panel) {
        this.props.updateLocation(`/flows/${this.props.flow.id}/${panel}`)
    }

    closePrompt(edit) {
        this.setState({ prompt: false })
        if (edit) {
            this.refs.tab.edit(edit)
        }
    }

    promptEdit() {
        let options

        switch (this.props.tab) {

            case 'request':
                options = [
                    'method',
                    'url',
                    { text: 'http version', key: 'v' },
                    'header'
                ]
                break

            case 'response':
                options = [
                    { text: 'http version', key: 'v' },
                    'code',
                    'message',
                    'header'
                ]
                break

            case 'details':
                return

            default:
                throw 'Unknown tab for edit: ' + this.props.tab
        }

        this.setState({ prompt: { options, done: this.closePrompt } })
    }

    render() {
        const tabs = this.getTabs()
        let { flow, tab: active, onUpdate } = this.props

        if (tabs.indexOf(active) < 0) {
            if (active === 'response' && flow.error) {
                active = 'error'
            } else if (active === 'error' && flow.response) {
                active = 'response'
            } else {
                active = tabs[0]
            }
        }

        const Tab = FlowView.allTabs[_.capitalize(active)]

        return (
            <div className="flow-detail" onScroll={this.adjustHead}>
                <Nav
                    flow={flow}
                    tabs={tabs}
                    active={active}
                    onSelectTab={this.selectTab}
                />
                <Tab ref="tab" flow={flow} onUpdate={onUpdate} />
                {this.state.prompt && (
                    <Prompt {...this.state.prompt}/>
                )}
            </div>
        )
    }
}
