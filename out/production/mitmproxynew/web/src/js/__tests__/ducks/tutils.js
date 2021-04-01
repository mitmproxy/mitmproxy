import React from 'react'
import { combineReducers, applyMiddleware, createStore as createReduxStore } from 'redux'
import thunk from 'redux-thunk'
import configureStore from 'redux-mock-store'
import { ConnectionState } from '../../ducks/connection'
import TFlow from './_tflow'

const mockStore = configureStore([thunk])

export function createStore(parts) {
    return createReduxStore(
        combineReducers(parts),
        applyMiddleware(...[thunk])
    )
}

export { TFlow }

export function TStore(){
    let tflow = new TFlow()
    return mockStore({
        ui: {
            flow: {
                contentView: 'Auto',
                displayLarge: false,
                showFullContent: true,
                maxContentLines: 10,
                content: ['foo', 'bar'],
                viewDescription: 'foo',
                modifiedFlow: true,
                tab: 'request'
            },
            header: {
                tab: 'Start'
            },
            modal: {
                activeModal: undefined
            },
            optionsEditor: {
                booleanOption: { isUpdating: true, error: false },
                strOption: { error: true },
                intOption: {},
                choiceOption: {},
            }
        },
        settings: {
            contentViews: ['Auto', 'Raw', 'Text'],
            anticache: true,
            anticomp: false
        },
        options: {
            booleanOption: {
                choices: null,
                default: false,
                help: "foo",
                type: "bool",
                value: false
            },
            strOption: {
                choices: null,
                default: null,
                help: "foo",
                type: "str",
                value: "str content"
            },
            intOption: {
                choices: null,
                default: 0,
                help: "foo",
                type: "int",
                value: 1
            },
            choiceOption: {
                choices: ['a', 'b', 'c'],
                default: 'a',
                help: "foo",
                type: "str",
                value: "b"
            },
        },
        flows: {
            selected: ["d91165be-ca1f-4612-88a9-c0f8696f3e29"],
            byId: {"d91165be-ca1f-4612-88a9-c0f8696f3e29": tflow},
            filter: '~u foo',
            highlight: '~a bar',
            sort: {
                desc: true,
                column: 'PathColumn'
            },
            view: [ tflow ]
        },
        connection: {
            state: ConnectionState.ESTABLISHED

        },
        eventLog: {
            visible: true,
            filters: {
                debug: true,
                info: true,
                web: false,
                warn: true,
                error: true
            },
            view: [
                { id: 1, level: 'info', message: 'foo' },
                { id: 2, level: 'error', message: 'bar' }
            ]
        }
    })
}
