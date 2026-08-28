import v25_fastnet as fastnet


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload


def test_chunks_use_100_name_batches():
    values = [f"name{i}" for i in range(205)]
    chunks = list(fastnet.chunks(values))
    assert [len(c) for c in chunks] == [100, 100, 5]


def test_bulk_lookup_maps_requested_usernames(monkeypatch):
    response = FakeResponse(
        200,
        {
            "data": [
                {"requestedUsername": "TakenOne", "name": "TakenOne", "id": 1},
                {"requestedUsername": "OtherTaken", "name": "OtherTaken", "id": 2},
            ]
        },
        {
            "x-ratelimit-limit": "500",
            "x-ratelimit-remaining": "499",
            "x-ratelimit-reset": "12",
        },
    )

    monkeypatch.setattr(fastnet._session, "post", lambda *a, **k: response)
    result = fastnet.bulk_existing(["takenone", "freeone", "othertaken"])

    assert result.ok
    assert result.existing == {"takenone", "othertaken"}
    assert result.rate_limit == 500
    assert result.rate_remaining == 499
    assert result.rate_reset == 12


def test_bulk_lookup_429_exposes_retry_information(monkeypatch):
    response = FakeResponse(429, {}, {"retry-after": "3"})
    monkeypatch.setattr(fastnet._session, "post", lambda *a, **k: response)

    result = fastnet.bulk_existing(["name"])
    assert not result.ok
    assert result.status_code == 429
    assert result.retry_after == 3
    assert result.error == "http_429"


def test_bulk_lookup_rejects_more_than_100_names():
    try:
        fastnet.bulk_existing([f"x{i}" for i in range(101)])
    except ValueError as exc:
        assert "at most 100" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_bulk_controller_aimd_and_cooldown():
    controller = fastnet.BulkConcurrencyController(
        workers=4, minimum=1, maximum=8
    )
    healthy = [fastnet.BulkLookupResult(["a"], {"a"}, True)]
    controller.observe(healthy)
    assert controller.workers == 4
    controller.observe(healthy)
    assert controller.workers == 5

    limited = [
        fastnet.BulkLookupResult(
            ["b"],
            set(),
            False,
            status_code=429,
            retry_after=2,
            error="http_429",
        )
    ]
    controller.observe(limited)
    assert controller.workers == 2
    assert controller.cooldown_seconds(limited) == 2


def test_bulk_existing_many_splits_thousand_names_into_ten_requests(monkeypatch):
    calls = []

    def fake_bulk(names, timeout=(3.05, 8.0)):
        calls.append(tuple(names))
        return fastnet.BulkLookupResult(
            requested=list(names),
            existing=set(names),
            ok=True,
            status_code=200,
        )

    monkeypatch.setattr(fastnet, "bulk_existing", fake_bulk)
    controller = fastnet.BulkConcurrencyController(
        workers=4, minimum=1, maximum=8
    )
    names = [f"name{i:04d}" for i in range(1000)]
    results, controller = fastnet.bulk_existing_many(names, controller)

    assert len(results) == 10
    assert len(calls) == 10
    assert all(len(call) == 100 for call in calls)
    assert sum(len(result.existing) for result in results) == 1000
