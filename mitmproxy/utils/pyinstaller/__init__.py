from pathlib import Path

here = Path(__file__).parent.absolute()


def hook_dirs() -> list[str]:
    return [str(here)]
