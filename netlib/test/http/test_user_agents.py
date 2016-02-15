from netlib.http import user_agents


def test_get_shortcut():
    assert user_agents.get_by_shortcut("c")[0] == "chrome"
    assert not user_agents.get_by_shortcut("_")
