import * as React from "react"
import FlowTableHead from '../../../components/FlowTable/FlowTableHead'
import {Provider} from 'react-redux'
import {TStore} from '../../ducks/tutils'
import {fireEvent, render, screen} from "@testing-library/react";
import {setSort} from "../../../ducks/flows";


test("FlowTableHead Component", async () => {

    const store = TStore(),
        {asFragment} = render(
            <Provider store={store}>
                <table>
                    <thead>
                    <FlowTableHead/>
                    </thead>
                </table>
            </Provider>
        )
    expect(asFragment()).toMatchSnapshot()

    fireEvent.click(screen.getByText("Size"))

    expect(store.getActions()).toStrictEqual([
            setSort("size", false)
        ]
    )
})
