import React from "react";
import { formatAddress } from "../../../components/FlowView/Connection";
import { render } from "../../test-utils";

describe("formatAddress", () => {
    it("should handle IPv4 addresses", () => {
        let { asFragment } = render(
            <table>
                <tbody>{formatAddress("Address", ["8.8.8.8", 53])}</tbody>
            </table>,
        );
        expect(asFragment()).toHaveTextContent("8.8.8.8:53");
    });
    it("should handle IPv6 addresses", () => {
        let { asFragment } = render(
            <table>
                <tbody>{formatAddress("Address", ["::1", 53, 0, 0])}</tbody>
            </table>,
        );
        expect(asFragment()).toHaveTextContent("[::1]:53");
    });
    it("should handle missing addresses", () => {
        let { asFragment } = render(
            <table>
                <tbody>{formatAddress("Address", undefined)}</tbody>
            </table>,
        );
        expect(asFragment()).not.toHaveTextContent("Address");
    });
});
