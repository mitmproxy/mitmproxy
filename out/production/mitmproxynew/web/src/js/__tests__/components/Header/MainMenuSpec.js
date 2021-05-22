jest.mock('../../../ducks/settings')

import React from 'react'
import renderer from 'react-test-renderer'
import  MainMenu, { setIntercept } from '../../../components/Header/MainMenu'
import { Provider } from 'react-redux'
import { update as updateSettings } from '../../../ducks/settings'
import { TStore } from '../../ducks/tutils'

describe('MainMenu Component', () => {
    let store = TStore()

    it('should render and connect to state', () => {
        let provider = renderer.create(
            <Provider store={store}>
                <MainMenu/>
            </Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle change on interceptInput', () => {
        setIntercept('foo')
        expect(updateSettings).toBeCalledWith({ intercept: 'foo' })
    })
})
