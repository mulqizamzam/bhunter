from bhunter.scope import Scope


def test_in_scope():
    s = Scope({"scope": {"in_scope": ["*.example.com"],
                         "out_of_scope": ["admin.example.com"]}})
    assert s.allows("https://api.example.com/x")
    assert not s.allows("https://admin.example.com/x")
    assert not s.allows("https://other.com/x")
