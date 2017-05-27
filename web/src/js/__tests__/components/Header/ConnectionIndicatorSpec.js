import React from 'react'
import renderer from 'react-test-renderer'
import ConnectedIndicator, { ConnectionIndicator } from '../../../components/Header/ConnectionIndicator'
import { ConnectionState } from '../../../ducks/connection'
import { Provider } from 'react-redux'
import { TStore } from '../../ducks/tutils'

describe('ConnectionIndicator Component', () => {

    it('should render INIT', () => {
        let connectionIndicator = renderer.create(
            <ConnectionIndicator state={ConnectionState.INIT}/>),
            tree = connectionIndicator.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render FETCHING', () => {
        let connectionIndicator = renderer.create(
            <ConnectionIndicator state={ConnectionState.FETCHING}/>),
            tree = connectionIndicator.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render ESTABLISHED', () => {
        let connectionIndicator = renderer.create(
            <ConnectionIndicator state={ConnectionState.ESTABLISHED}/>),
            tree = connectionIndicator.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render ERROR', () => {
        let connectionIndicator = renderer.create(
            <ConnectionIndicator state={ConnectionState.ERROR} message="foo"/>),
            tree = connectionIndicator.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render OFFLINE', () => {
        let connectionIndicator = renderer.create(
            <ConnectionIndicator state={ConnectionState.OFFLINE} />),
            tree = connectionIndicator.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should connect to state', () => {
        let store = TStore(),
            provider = renderer.create(
            <Provider store={store}>
                <ConnectedIndicator/>
            </Provider>),
        tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

