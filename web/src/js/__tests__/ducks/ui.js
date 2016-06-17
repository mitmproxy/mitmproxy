jest.unmock("../../ducks/ui");

import reducer, {setActiveMenu, SELECT_FLOW} from '../../ducks/ui';


describe("ui reducer", () => {
    it("should return the initial state", () => {
        expect(reducer(undefined, {})).toEqual({ activeMenu: 'Start'})
    }),
    it("should return the state for view", () => {
        expect(reducer(undefined, setActiveMenu('View'))).toEqual({ activeMenu: 'View'})
    }),
    it("should change the state to Start", () => {
        expect(reducer({activeMenu: 'Flow'},
            { type: SELECT_FLOW,
              currentSelection: '1',
              flowId : undefined
            })).toEqual({ activeMenu: 'Start'})
    }),
    it("should change the state to Flow", () => {
        expect(reducer({activeMenu: 'Start'},
            { type: SELECT_FLOW,
              currentSelection: undefined,
              flowId : '1'
            })).toEqual({ activeMenu: 'Flow'})
    }),
    it("should not change the state", () => {
        expect(reducer({activeMenu: 'Options'},
            { type: SELECT_FLOW,
              currentSelection: '1',
              flowId : '2'
            })).toEqual({ activeMenu: 'Options'})
    })
});
