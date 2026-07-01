from packages.tooling.officecli import advanced


def test_office_command_strips_binary_name(monkeypatch):
    captured = {}

    def fake_run(args, expect_json=True, timeout=120):
        captured["args"] = args
        captured["expect_json"] = expect_json
        captured["timeout"] = timeout
        return {"success": True}

    monkeypatch.setattr(advanced, "run_officecli", fake_run)

    result = advanced.office_command(
        args=["officecli", "watch", "deck.pptx"],
        expect_json=False,
        timeout=30,
    )

    assert result == {"success": True}
    assert captured["args"] == ["watch", "deck.pptx"]
    assert captured["expect_json"] is False
    assert captured["timeout"] == 30


def test_office_mark_formats_props(monkeypatch):
    captured = {}

    def fake_run(args):
        captured["args"] = args
        return {"success": True}

    monkeypatch.setattr(advanced, "run_officecli", fake_run)

    advanced.office_mark(
        file_path="deck.pptx",
        path="/slide[1]/shape[1]",
        props={"color": "red", "note": "check"},
    )

    assert captured["args"] == [
        "watch",
        "deck.pptx",
        "mark",
        "deck.pptx",
        "/slide[1]/shape[1]",
        "--prop",
        "color=red",
        "--prop",
        "note=check",
    ]


def test_dump_pptx_adds_optional_out(monkeypatch):
    captured = {}

    def fake_run(args):
        captured["args"] = args
        return {"success": True}

    monkeypatch.setattr(advanced, "run_officecli", fake_run)

    advanced.dump_pptx(
        file_path="deck.pptx",
        path="/slide[1]",
        format="batch",
        out="slide1.json",
    )

    assert captured["args"] == [
        "dump",
        "deck.pptx",
        "/slide[1]",
        "--format",
        "batch",
        "--out",
        "slide1.json",
    ]
