jest.mock('../../../flow/utils')

import * as React from "react"
import renderer from 'react-test-renderer'
import FlowMenu from '../../../components/Header/FlowMenu'
import { TFlow, TStore }from '../../ducks/tutils'
import { MessageUtils } from "../../../flow/utils"
import { Provider } from 'react-redux'

describe('FlowMenu Component', () => {
    let tflow = new TFlow(),
        store = new TStore()
    tflow.modified = true
    tflow.intercepted = true
    global.fetch = jest.fn()

    let flowMenu = renderer.create(
            <Provider store={store}>
                <FlowMenu />
            </Provider>
        ),
        tree = flowMenu.toJSON()

    it('should render correctly with flow', () => {
        expect(tree).toMatchSnapshot()
    })

    let menu_content_2 = tree.children[1].children[0]
    it('should handle download', () => {
        let button = menu_content_2.children[0]
        button.props.onClick()
        expect(MessageUtils.getContentURL).toBeCalledWith(tflow, tflow.response)
    })

})
