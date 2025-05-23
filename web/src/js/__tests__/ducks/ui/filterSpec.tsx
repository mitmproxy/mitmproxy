import reducer, {
    FilterName,
    setFilter,
    setHighlight,
} from "../../../ducks/ui/filter";

jest.mock("../../../utils");

test("filter reducer", () => {
    expect(reducer(undefined, setFilter("foo"))).toEqual({
        [FilterName.Search]: "foo",
        [FilterName.Highlight]: "",
    });

    expect(reducer(undefined, setHighlight("foo"))).toEqual({
        [FilterName.Search]: "",
        [FilterName.Highlight]: "foo",
    });
});
