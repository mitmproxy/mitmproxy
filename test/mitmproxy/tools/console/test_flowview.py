from mitmproxy.test import tflow


async def test_flowview(monkeypatch, console):
    for f in tflow.tflows():
        console.commands.call("view.clear")
        await console.load_flow(f)
        console.type("<enter><tab><tab>")
