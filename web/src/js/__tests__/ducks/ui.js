jest.unmock("../../ducks/ui");
// @todo fix it ( this is why I don't like to add tests until our architecture is stable :P )
jest.unmock("../../ducks/views/main");

import reducer, { setActiveMenu } from '../../ducks/ui';
import { SELECT } from '../../ducks/views/main';

describe("ui reducer", () => {
    it("should return the initial state", () => {
        expect(reducer(undefined, {})).toEqual({ activeMenu: 'Start'})
    }),
    it("should return the state for view", () => {
        expect(reducer(undefined, setActiveMenu('View'))).toEqual({ activeMenu: 'View'})
    }),
    it("should change the state to Start when deselecting a flow and we a currently at the flow tab", () => {
        expect(reducer({activeMenu: 'Flow'},
            { type: SELECT,
              currentSelection: '1',
              flowId : undefined
            })).toEqual({ activeMenu: 'Start'})
    }),
    it("should change the state to Flow when we selected a flow and no flow was selected before", () => {
        expect(reducer({activeMenu: 'Start'},
            { type: SELECT,
              currentSelection: undefined,
              flowId : '1'
            })).toEqual({ activeMenu: 'Flow'})
    }),
    it("should not change the state to Flow when OPTIONS tab is selected and we selected a flow and a flow as selected before", () => {
        expect(reducer({activeMenu: 'Options'},
            { type: SELECT,
              currentSelection: '1',
              flowId : '2'
            })).toEqual({ activeMenu: 'Options'})
    })
});
