import { ModeState, RawSpecParts } from ".";

export interface Process {
    is_visible: boolean;
    executable: string;
    is_system: string;
    display_name: string;
}

export interface LocalState extends ModeState {
    selectedApplications?: string;
}

export const getSpec = (m: LocalState): string => {
    return m.selectedApplications ? `local:${m.selectedApplications}` : "local";
};

export const parseRaw = ({ data }: RawSpecParts): LocalState => ({
    ui_id: Math.random(),
    active: true,
    selectedApplications: data,
});
