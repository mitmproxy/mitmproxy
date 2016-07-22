import React, { Component } from 'react'
import { connect } from 'react-redux'
import _ from 'lodash'

import Nav from './FlowView/Nav'
import { Request, Response, ErrorView as Error } from './FlowView/Messages'
import Details from './FlowView/Details'
import Prompt from './Prompt'

import { selectTab } from '../ducks/ui/flow'
import { setPrompt } from '../ducks/ui/prompt'
import { setEditType } from '../ducks/ui/focus'

export default class FlowView extends Component {

    static allTabs = { Request, Response, Error, Details }

    static focusTarget = {
        request: {
            m: 'method',
            u: 'url',
            v: 'httpVersion',
            h: 'headers',
        },
        response: {
            c: 'status_code',
            m: 'msg',
            v: 'httpVersion',
            h: 'headers'
        },
    }

    componentDidUpdate() {
        if (this.props.editType) {
            this.props.setEditType(null)
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
                <Tab editType={this.props.editType} flow={flow} updateFlow={updateFlow} />
                {this.props.prompt && (
                    <Prompt options={this.prompt} done={editType => {
                        setPrompt(null)
                        setEditType(FlowView.focusTarget[active][editType])
                    }} />
                )}
            </div>
        )
    }
}

export default connect(
    state => ({
        prompt: state.ui.prompt.options,
        editType: state.ui.focus.editType,
        tab: state.ui.flow.tab,
    }),
    {
        selectTab,
        setPrompt,
        setEditType,
    }
)(FlowView)
