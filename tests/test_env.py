from resumable.runtime import Env


def test_env_lookup_walks_parent_chain() -> None:
    root = Env({"x": 1}, name="root")
    middle = Env(enclosing=root, name="middle")
    leaf = Env(enclosing=middle, name="leaf")

    assert leaf["x"] == 1


def test_env_define_shadows_parent_binding() -> None:
    root = Env({"x": 1}, name="root")
    leaf = Env(enclosing=root, name="leaf")

    leaf.define("x", 99)

    assert leaf["x"] == 99
    assert root["x"] == 1


def test_env_setitem_updates_nearest_ancestor_binding() -> None:
    root = Env({"x": 1}, name="root")
    middle = Env({"x": 10}, enclosing=root, name="middle")
    leaf = Env(enclosing=middle, name="leaf")

    leaf["x"] = 11

    assert middle["x"] == 11
    assert root["x"] == 1


def test_env_all_vars_single_scope_shape() -> None:
    env = Env({"x": 1, "name": "alice"}, name="local")

    assert env.all_vars() == {
        "name": "local",
        "self": [("x", 1), ("name", "alice")],
        "parent_env": None,
    }


def test_env_all_vars_nested_scope_shape() -> None:
    root = Env({"x": 1}, name="root")
    child = Env({"y": 2}, enclosing=root, name="child")
    leaf = Env({"z": 3}, enclosing=child, name="leaf")

    assert leaf.all_vars() == {
        "name": "leaf",
        "self": [("z", 3)],
        "parent_env": {
            "name": "child",
            "self": [("y", 2)],
            "parent_env": {
                "name": "root",
                "self": [("x", 1)],
                "parent_env": None,
            },
        },
    }
