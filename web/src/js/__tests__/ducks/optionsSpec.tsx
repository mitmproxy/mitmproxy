import reduceOptions, * as OptionsActions from '../../ducks/options'
import * as OptionsEditorActions from '../../ducks/ui/optionsEditor'
import {enableFetchMocks} from "jest-fetch-mock";
import {TStore} from "./tutils";


describe('option reducer', () => {
    it('should return initial state', () => {
        expect(reduceOptions(undefined, {type: "other"})).toEqual(OptionsActions.defaultState)
    })

    it('should handle receive action', () => {
        let action = {type: OptionsActions.RECEIVE, data: {id: {value: 'foo'}}}
        expect(reduceOptions(undefined, action)).toEqual({id: 'foo'})
    })

    it('should handle update action', () => {
        let action = {type: OptionsActions.UPDATE, data: {id: {value: 1}}}
        expect(reduceOptions(undefined, action)).toEqual({...OptionsActions.defaultState, id: 1})
    })
})

test("sendUpdate", async () => {
    enableFetchMocks();
    let store = TStore();

    fetchMock.mockResponseOnce("fooerror", {status: 404});
    await store.dispatch(dispatch => OptionsActions.pureSendUpdate("intercept", "~~~", dispatch))
    expect(store.getActions()).toEqual([
        OptionsEditorActions.updateError("intercept", "fooerror")
    ])

    store.clearActions();
    fetchMock.mockResponseOnce("", {status: 200});
    await store.dispatch(dispatch => OptionsActions.pureSendUpdate("intercept", "valid", dispatch))
    expect(store.getActions()).toEqual([
        OptionsEditorActions.updateSuccess("intercept")
    ])

});

test("save", async () => {
    enableFetchMocks();
    fetchMock.mockResponseOnce("");
    let store = TStore();
    await store.dispatch(OptionsActions.save());
    expect(fetchMock).toBeCalled();
});

test("addInterceptFilter", async () => {
    enableFetchMocks();
    fetchMock.mockClear();
    fetchMock.mockResponses("", "");
    let store = TStore();
    await store.dispatch(OptionsActions.addInterceptFilter("~u foo"));
    expect(fetchMock.mock.calls[0][1]?.body).toEqual('{"intercept":"~u foo"}');
    store.getState().options.intercept = "~u foo";

    await store.dispatch(OptionsActions.addInterceptFilter("~u foo"));
    expect(fetchMock.mock.calls).toHaveLength(1);

    await store.dispatch(OptionsActions.addInterceptFilter("~u bar"));
    expect(fetchMock.mock.calls[1][1]?.body).toEqual('{"intercept":"~u foo | ~u bar"}');


});
