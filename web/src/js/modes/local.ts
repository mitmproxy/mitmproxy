import { ModeState, RawSpecParts } from ".";

export interface LocalState extends ModeState {
    applications?: string;
}

export const getSpec = (m: LocalState): string => {
    return m.applications ? `local:${m.applications}` : "local";
};

export const parseRaw = ({ data }: RawSpecParts): LocalState => ({
    ui_id: Math.random(),
    active: true,
    applications: data,
});
