import * as React from "react";
import renderer from "react-test-renderer";
import FileMenu from "../../../components/Header/FileMenu";
import { Provider } from "react-redux";
import { TStore } from "../../ducks/tutils";

describe("FileMenu Component", () => {
    const store = TStore();
    const fileMenu = renderer.create(
        <Provider store={store}>
            <FileMenu />
        </Provider>,
    );
    const tree = fileMenu.toJSON();

    it("should render correctly", () => {
        expect(tree).toMatchSnapshot();
    });
});
