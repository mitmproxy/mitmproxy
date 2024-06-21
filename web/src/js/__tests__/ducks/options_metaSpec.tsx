import reduceOptionsMeta, * as OptionsMetaActions from "../../ducks/options_meta";
import * as OptionsActions from "../../ducks/options";

test("options_meta", async () => {
    expect(reduceOptionsMeta(undefined, { type: "other" })).toEqual(
        OptionsMetaActions.defaultState,
    );

    expect(
        reduceOptionsMeta(undefined, {
            type: OptionsActions.RECEIVE,
            data: { id: { value: "foo" } },
        }),
    ).toEqual({ id: { value: "foo" } });

    expect(
        reduceOptionsMeta(undefined, {
            type: OptionsActions.UPDATE,
            data: { id: { value: 1 } },
        }),
    ).toEqual({ ...OptionsMetaActions.defaultState, id: { value: 1 } });
});
