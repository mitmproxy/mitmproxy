import * as React from "react";
import renderer from "react-test-renderer";
import { PureOptionDefault } from "../../../components/Modal/OptionModal";

describe("PureOptionDefault Component", () => {
    it("should return null when the value is default", () => {
        const pureOptionDefault = renderer.create(
            <PureOptionDefault value="foo" defaultVal="foo" />,
        );
        const tree = pureOptionDefault.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should handle boolean type", () => {
        const pureOptionDefault = renderer.create(
            <PureOptionDefault value={true} defaultVal={false} />,
        );
        const tree = pureOptionDefault.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should handle array", () => {
        let a = [""],
            b = [],
            c = ["c"],
            pureOptionDefault = renderer.create(
                <PureOptionDefault value={a} defaultVal={b} />,
            ),
            tree = pureOptionDefault.toJSON();
        expect(tree).toMatchSnapshot();

        pureOptionDefault = renderer.create(
            <PureOptionDefault value={a} defaultVal={c} />,
        );
        tree = pureOptionDefault.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should handle string", () => {
        const pureOptionDefault = renderer.create(
            <PureOptionDefault value="foo" defaultVal="" />,
        );
        const tree = pureOptionDefault.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should handle null value", () => {
        const pureOptionDefault = renderer.create(
            <PureOptionDefault value="foo" defaultVal={null} />,
        );
        const tree = pureOptionDefault.toJSON();
        expect(tree).toMatchSnapshot();
    });
});
