import React, { Component } from 'react'
import { connect } from 'react-redux'
import _ from 'lodash'

import Nav from './FlowView/Nav'
import { Request, Response, ErrorView as Error } from './FlowView/Messages'
import Details from './FlowView/Details'
import Prompt from './Prompt'

import { setPrompt, selectTab } from '../ducks/ui'

export default class FlowView extends Component {

    static allTabs = { Request, Response, Error, Details }

    constructor(props, context) {
        super(props, context)
        this.onPromptFinish = this.onPromptFinish.bind(this)
    }

    onPromptFinish(edit) {
        this.props.setPrompt(false)
        if (edit && this.tabComponent) {
            this.tabComponent.edit(edit)
        }
    }

    getPromptOptions() {
        switch (this.props.tab) {

            case 'request':
                return [
                    'method',
                    'url',
                    { text: 'http version', key: 'v' },
                    'header'
                ]
                break

            case 'response':
                return [
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
    }

    render() {
        let { flow, tab: active, updateFlow } = this.props
        const tabs = ['request', 'response', 'error'].filter(k => flow[k]).concat(['details'])

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
                    onSelectTab={this.props.selectTab}
                />
                <Tab ref={ tab => this.tabComponent = tab } flow={flow} updateFlow={updateFlow} />
                {this.state.prompt && (
                    <Prompt options={this.getPromptOptions()} done={this.onPromptFinish} />
                )}
            </div>
        )
    }
}

export default connect(
    state => ({
        needEdit: state.ui.needEdit,
    }),
    {
        setPrompt,
        selectTab,
    }
)(FlowView)
