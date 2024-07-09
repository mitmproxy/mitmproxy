import * as React from "react";
import renderer from "react-test-renderer";
import { Provider } from "react-redux";
import OptionMenu from "../../../components/Header/OptionMenu";
import { TStore } from "../../ducks/tutils";

describe("OptionMenu Component", () => {
    it("should render correctly", () => {
        const store = TStore();
        const provider = renderer.create(
            <Provider store={store}>
                <OptionMenu />
            </Provider>,
        );
        const tree = provider.toJSON();
        expect(tree).toMatchSnapshot();
    });
});
