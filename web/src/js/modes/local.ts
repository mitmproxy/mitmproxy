import { ModeState, RawSpecParts } from ".";

export interface LocalState extends ModeState {
    selectedProcesses?: string;
}

export const getSpec = (m: LocalState): string => {
    return m.selectedProcesses ? `local:${m.selectedProcesses}` : "local";
};

export const parseRaw = ({ data }: RawSpecParts): LocalState => ({
    ui_id: Math.random(),
    active: true,
    selectedProcesses: data,
});
