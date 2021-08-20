import * as React from "react"
import {render as rtlRender} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import "@testing-library/jest-dom"
import {Provider} from 'react-redux'
// Import your own reducer
import {createAppStore} from '../ducks'
import {testState} from "./ducks/tutils";

// re-export everything
export {
    waitFor, fireEvent, act, screen
} from '@testing-library/react'
export {
    userEvent
}

export function render(
    ui,
    {
        store = createAppStore(testState),
        ...renderOptions
    } = {}
) {
    function Wrapper({children}) {
        return <Provider store={store}>{children}</Provider>
    }

    const ret = rtlRender(ui, {wrapper: Wrapper, ...renderOptions})
    return {...ret, store}
}
