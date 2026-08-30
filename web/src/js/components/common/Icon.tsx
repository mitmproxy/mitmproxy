import * as React from "react";
import classnames from "classnames";
import type { LucideIcon } from "lucide-react";
import {
    AlertTriangle,
    AppWindow,
    ArrowLeft,
    ArrowLeftRight,
    ArrowRight,
    Ban,
    Braces,
    Bug,
    Cable,
    Check,
    ChevronsDown,
    ChevronDown,
    ChevronRight,
    ChevronUp,
    CircleQuestionMark,
    CircleX,
    Clipboard,
    CodeXml,
    Copy,
    CopyPlus,
    CornerUpRight,
    Download,
    ExternalLink,
    File,
    FileCheck,
    FileOutput,
    Files,
    FolderOpen,
    Globe,
    History,
    Highlighter,
    Image as ImageIcon,
    Info,
    LoaderCircle,
    Paintbrush,
    Palette,
    Pause,
    Pencil,
    Play,
    Redo2,
    RefreshCw,
    Save,
    Search,
    Send,
    Settings,
    Square,
    SquareCheck,
    SquarePlus,
    StepForward,
    Terminal,
    Trash2,
    Upload,
    X,
    Zap,
} from "lucide-react";

export const iconsMap = {
    abort: X,
    addSquare: SquarePlus,
    arrowLeft: ArrowLeft,
    arrowRight: ArrowRight,
    braces: Braces,
    browser: AppWindow,
    cable: Cable,
    chevronDown: ChevronDown,
    chevronRight: ChevronRight,
    chevronUp: ChevronUp,
    close: X,
    closeCircle: CircleX,
    clipboard: Clipboard,
    code: CodeXml,
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
    file: File,
    fileCheck: FileCheck,
    files: Files,
    globe: Globe,
    help: CircleQuestionMark,
    highlight: Highlighter,
    image: ImageIcon,
    info: Info,
    intercept: Pause,
    loading: LoaderCircle,
    mark: Paintbrush,
    openFolder: FolderOpen,
    palette: Palette,
    pause: Pause,
    redirect: CornerUpRight,
    replay: Redo2,
    refresh: RefreshCw,
    revert: History,
    resume: Play,
    resumeAll: StepForward,
    save: Save,
    search: Search,
    send: Send,
    settings: Settings,
    square: Square,
    swap: ArrowLeftRight,
    terminal: Terminal,
    upload: Upload,
    warning: AlertTriangle,
    zap: Zap,
} as const satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof iconsMap;

type IconProps = {
    name: IconName;
    size?: number;
    strokeWidth?: number;
    className?: string;
    onClick?: React.MouseEventHandler<SVGSVGElement>;
    "aria-label"?: string;
    title?: string;
};

export default function Icon({
    name,
    size = 16,
    strokeWidth = 2,
    className,
    onClick,
    "aria-label": ariaLabel,
    title,
}: IconProps) {
    const SvgIcon = iconsMap[name];
    const decorative = !ariaLabel && !title;

    return (
        <SvgIcon
            size={size}
            strokeWidth={strokeWidth}
            className={classnames("icon", `icon-${name}`, className)}
            onClick={onClick}
            aria-label={ariaLabel}
            aria-hidden={decorative || undefined}
        >
            {title ? <title>{title}</title> : null}
        </SvgIcon>
    );
}
