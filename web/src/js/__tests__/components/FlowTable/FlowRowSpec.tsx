import * as React from "react"
import FlowRow from '../../../components/FlowTable/FlowRow'
import {testState} from '../../ducks/tutils'
import {fireEvent, render, screen} from "../../test-utils";
import {createAppStore} from "../../../ducks";


test("FlowRow", async () => {
    const store = createAppStore(testState),
        tflow2 = store.getState().flows.list[0],
        {asFragment} = render(<table>
            <tbody>
            <FlowRow flow={tflow2} selected highlighted/>
            </tbody>
        </table>, {store})
    expect(asFragment()).toMatchSnapshot()

    expect(store.getState().flows.selected[0]).not.toBe(store.getState().flows.list[0].id)
    fireEvent.click(screen.getByText("http://address:22/path"))
    expect(store.getState().flows.selected[0]).toBe(store.getState().flows.list[0].id)
})
