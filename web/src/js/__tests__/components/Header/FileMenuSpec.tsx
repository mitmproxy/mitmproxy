import * as React from "react";
import FileMenu from "../../../components/Header/FileMenu";
import { Provider } from "react-redux";
import { TStore } from "../../ducks/tutils";
import { render } from "../../test-utils";

describe("FileMenu Component", () => {
    const store = TStore();
    const { asFragment } = render(
        <Provider store={store}>
            <FileMenu />
        </Provider>,
    );

    it("should render correctly", () => {
        expect(asFragment()).toMatchSnapshot();
    });
});
