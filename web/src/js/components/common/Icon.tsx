import * as React from "react";
import classnames from "classnames";
import type { LucideIcon } from "lucide-react";
import {
    AlertTriangle,
    AppWindow,
    ArrowLeft,
    ArrowRight,
    Ban,
    Bug,
    Check,
    ChevronsDown,
    ChevronDown,
    ChevronRight,
    ChevronUp,
    CircleQuestionMark,
    CircleX,
    Clipboard,
    Copy,
    CopyPlus,
    Download,
    ExternalLink,
    FileOutput,
    Files,
    FolderOpen,
    History,
    Highlighter,
    Info,
    LoaderCircle,
    Paintbrush,
    Pause,
    Pencil,
    Play,
    Redo2,
    RefreshCw,
    Save,
    Search,
    Settings,
    Square,
    SquareCheck,
    SquarePlus,
    StepForward,
    Terminal,
    Trash2,
    Upload,
    X,
} from "lucide-react";

export const iconsMap = {
    abort: X,
    addSquare: SquarePlus,
    arrowLeft: ArrowLeft,
    arrowRight: ArrowRight,
    browser: AppWindow,
    chevronDown: ChevronDown,
    chevronRight: ChevronRight,
    chevronUp: ChevronUp,
    close: X,
    closeCircle: CircleX,
    clipboard: Clipboard,
    confirm: Check,
    confirmSquare: SquareCheck,
    copy: Copy,
    debug: Bug,
    delete: Trash2,
    download: Download,
    duplicate: CopyPlus,
    edit: Pencil,
    error: Ban,
    expandMore: ChevronsDown,
    export: FileOutput,
    external: ExternalLink,
    files: Files,
    help: CircleQuestionMark,
    highlight: Highlighter,
    info: Info,
    intercept: Pause,
    loading: LoaderCircle,
    mark: Paintbrush,
    openFolder: FolderOpen,
    pause: Pause,
    replay: Redo2,
    refresh: RefreshCw,
    revert: History,
    resume: Play,
    resumeAll: StepForward,
    save: Save,
    search: Search,
    settings: Settings,
    square: Square,
    terminal: Terminal,
    upload: Upload,
    warning: AlertTriangle,
} as const satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof iconsMap;

type IconProps = {
    name: IconName;
    size?: number;
    strokeWidth?: number;
    className?: string;
    onClick?: React.MouseEventHandler<SVGSVGElement>;
    "aria-label"?: string;
};

export default function Icon({
    name,
    size = 16,
    strokeWidth = 2,
    className,
    onClick,
    "aria-label": ariaLabel,
}: IconProps) {
    const SvgIcon = iconsMap[name];
    const decorative = !ariaLabel;

    return (
        <SvgIcon
            size={size}
            strokeWidth={strokeWidth}
            className={classnames("icon", `icon-${name}`, className)}
            onClick={onClick}
            aria-label={ariaLabel}
            aria-hidden={decorative || undefined}
        />
    );
}
