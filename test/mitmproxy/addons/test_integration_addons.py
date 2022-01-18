import asyncio
import inspect
import json

from mitmproxy.tools import main


def create_test_addon():
    import typing
    import json
    from mitmproxy import ctx

    class OptionsE2ETestAddon:
        def load(self, loader):
            loader.add_option(
                "e2e_test_results_file",
                typing.Optional[str],
                None,
                "file to output results to"
            )
            loader.add_option(
                "e2e_test_str",
                typing.Optional[str],
                None,
                "optional str test option"
            )
            loader.add_option(
                "e2e_test_str_seq",
                typing.Sequence[str],
                (),
                "str seq test option"
            )

        def configure(self, updated):
            if "e2e_test_results_file" in updated:
                results = {
                    "e2e_test_str": ctx.options.e2e_test_str,
                    "e2e_test_str_seq": ctx.options.e2e_test_str_seq,
                }
                assert ctx.options.e2e_test_results_file
                with open(ctx.options.e2e_test_results_file, "w") as f:
                    json.dump(results, f, indent=2)

    return OptionsE2ETestAddon()


def test_config_with_addon_options(event_loop, tdata, tmpdir):
    with open(tmpdir / "config.yaml", "w") as f:
        config = """
        e2e_test_str: e2e_test_str_value
        e2e_test_str_seq: [
            value1,
            value2
        ]
        """
        f.write(inspect.cleandoc(config))

    addon_path = tmpdir / "test_config_addon.py"
    with open(addon_path, "w") as f:
        f.write(inspect.getsource(create_test_addon))
        f.write("\n")
        f.write("addons = [create_test_addon()]\n")

    results_file = tmpdir / "test_config_results.json"

    asyncio.set_event_loop(event_loop)
    main.mitmdump([
        "--no-server",
        "--set", "confdir=" + str(tmpdir),
        "--scripts", str(addon_path),
        "--set", "e2e_test_results_file=" + str(results_file),
        "--scripts", tdata.path("mitmproxy/data/addonscripts/shutdown.py"),
    ])

    expected = {
        "e2e_test_str": "e2e_test_str_value",
        "e2e_test_str_seq": ["value1", "value2"],
    }
    with open(results_file, "r") as f:
        actual = json.load(f)
        assert expected == actual
