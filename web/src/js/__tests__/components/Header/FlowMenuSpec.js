jest.mock('../../../flow/utils')

import React from 'react'
import renderer from 'react-test-renderer'
import ConnectedFlowMenu, { FlowMenu } from '../../../components/Header/FlowMenu'
import { TFlow, TStore }from '../../ducks/tutils'
import { MessageUtils } from "../../../flow/utils"
import { Provider } from 'react-redux'

describe('FlowMenu Component', () => {
    let actions = {
        resumeFlow: jest.fn(),
        killFlow: jest.fn(),
        replayFlow: jest.fn(),
        duplicateFlow: jest.fn(),
        removeFlow: jest.fn(),
        revertFlow: jest.fn()
    },
        tflow = new TFlow()
    tflow.modified = true
    tflow.intercepted = true

    it('should render correctly without flow', () => {
        let flowMenu = renderer.create(
                <FlowMenu removeFlow={actions.removeFlow}
                           killFlow={actions.killFlow}
                           replayFlow={actions.replayFlow}
                           duplicateFlow={actions.duplicateFlow}
                           resumeFlow={actions.resumeFlow}
                           revertFlow={actions.revertFlow}/>),
            tree = flowMenu.toJSON()
            expect(tree).toMatchSnapshot()
    })

    let flowMenu = renderer.create(<FlowMenu
                            flow={tflow}
                            removeFlow={actions.removeFlow}
                            killFlow={actions.killFlow}
                            replayFlow={actions.replayFlow}
                            duplicateFlow={actions.duplicateFlow}
                            resumeFlow={actions.resumeFlow}
                            revertFlow={actions.revertFlow}/>),
        tree = flowMenu.toJSON()

    it('should render correctly with flow', () => {
        expect(tree).toMatchSnapshot()
    })

    let menu_content_1 = tree.children[0].children[0]
    it('should handle replayFlow', () => {
        let button = menu_content_1.children[0]
        button.props.onClick()
        expect(actions.replayFlow).toBeCalledWith(tflow)
    })

    it('should handle duplicateFlow', () => {
        let button = menu_content_1.children[1]
        button.props.onClick()
        expect(actions.duplicateFlow).toBeCalledWith(tflow)
    })

    it('should handle revertFlow', () => {
        let button = menu_content_1.children[2]
        button.props.onClick()
        expect(actions.revertFlow).toBeCalledWith(tflow)
    })

    it('should handle removeFlow', () => {
        let button = menu_content_1.children[3]
        button.props.onClick()
        expect(actions.removeFlow).toBeCalledWith(tflow)
    })

    let menu_content_2 = tree.children[1].children[0]
    it('should handle download', () => {
        let button = menu_content_2.children[0]
        button.props.onClick()
        expect(MessageUtils.getContentURL).toBeCalledWith(tflow, tflow.response)
    })

    let menu_content_3 = tree.children[2].children[0]
    it('should handle resumeFlow', () => {
        let button = menu_content_3.children[0]
        button.props.onClick()
        expect(actions.resumeFlow).toBeCalledWith(tflow)
    })

    it('should handle killFlow', () => {
        let button = menu_content_3.children[1]
        button.props.onClick()
        expect(actions.killFlow).toBeCalledWith(tflow)
    })

    it('should connect to state', () => {
        let store = TStore(),
            provider = renderer.create(<Provider store={store}><ConnectedFlowMenu/></Provider>),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })

})
