#!/usr/bin/env python3
import asyncio
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

import tomllib

root = Path(__file__).parent.parent.absolute()


async def main():
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    exclude = re.compile(
        "|".join(
            f"({fnmatch.translate(x)})"
            for x in data["tool"]["pytest"]["individual_coverage"]["exclude"]
        )
    )

    sem = asyncio.Semaphore(os.cpu_count() or 1)

    async def run_tests(f: Path, should_fail: bool) -> None:
        if f.name == "__init__.py":
            test_file = Path("test") / f.parent.with_name(f"test_{f.parent.name}.py")
        else:
            test_file = Path("test") / f.with_name(f"test_{f.name}")

        coverage_file = f".coverage-{str(f).replace('/','-')}"

        async with sem:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "pytest",
                    "-qq",
                    "--disable-pytest-warnings",
                    "--cov",
                    str(f.with_suffix("")).replace("/", "."),
                    "--cov-fail-under",
                    "100",
                    "--cov-report",
                    "term-missing:skip-covered",
                    test_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={
                        "COVERAGE_FILE": coverage_file,
                        **os.environ,
                    },
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), 60)
            except TimeoutError:
                raise RuntimeError(f"{f}: timeout")
            finally:
                Path(coverage_file).unlink(missing_ok=True)

            if should_fail:
                if proc.returncode != 0:
                    print(f"{f}: excluded")
                else:
                    raise RuntimeError(
                        f"{f} is now fully covered by {test_file}. Remove it from tool.pytest.individual_coverage in pyproject.toml."
                    )
            else:
                if proc.returncode == 0:
                    print(f"{f}: ok")
                else:
                    raise RuntimeError(
                        f"{f} is not fully covered by {test_file}:\n{stdout.decode(errors='ignore')}\n{stderr.decode(errors='ignore')}"
                    )

    tasks = []
    for f in (root / "mitmproxy").glob("**/*.py"):
        f = f.relative_to(root)

        if len(sys.argv) > 1 and sys.argv[1] not in str(f):
            continue

        if f.name == "__init__.py" and f.stat().st_size == 0:
            print(f"{f}: empty")
            continue

        tasks.append(
            asyncio.create_task(run_tests(f, should_fail=exclude.match(str(f))))
        )

    exit_code = 0
    for task in asyncio.as_completed(tasks):
        try:
            await task
        except RuntimeError as e:
            print(e)
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
