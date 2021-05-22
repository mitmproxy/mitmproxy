import React from 'react'
import renderer from 'react-test-renderer'
import { MenuToggle, SettingsToggle, EventlogToggle } from '../../../components/Header/MenuToggle'
import { Provider } from 'react-redux'
import { REQUEST_UPDATE } from '../../../ducks/settings'
import { TStore } from '../../ducks/tutils'

global.fetch = jest.fn()

describe('MenuToggle Component', () => {
    it('should render correctly', () => {
        let changeFn = jest.fn(),
            menuToggle = renderer.create(
                <MenuToggle onChange={changeFn} value={true}>
                    <p>foo children</p>
                </MenuToggle>),
            tree = menuToggle.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

describe('SettingToggle Component', () => {
    let store = TStore(),
        provider = renderer.create(
            <Provider store={store}>
                <SettingsToggle setting='anticache'>
                    <p>foo children</p>
                </SettingsToggle>
            </Provider>),
        tree = provider.toJSON()

    it('should render and connect to state', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle change', () => {
        let menuToggle = tree.children[0].children[0]
        menuToggle.props.onChange()
        expect(store.getActions()).toEqual([{ type: REQUEST_UPDATE }])
    })
})

describe('EventlogToggle Component', () => {
    let store = TStore(),
        changFn = jest.fn(),
        provider = renderer.create(
            <Provider store={store}>
                <EventlogToggle value={false} onChange={changFn}/>
            </Provider>
        ),
        tree = provider.toJSON()
    it('should render and connect to state', () => {
        expect(tree).toMatchSnapshot()
    })
})
