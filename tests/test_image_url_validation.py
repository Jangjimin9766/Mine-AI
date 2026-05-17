from app.core import searcher


def test_validate_image_url_blocks_unstable_hosts_without_network(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("network validation should not run for blocked hosts")

    monkeypatch.setattr(searcher.requests, "head", fail_if_called)

    blocked_urls = [
        "https://lookaside.instagram.com/seo/google_widget/crawler/?media_id=1",
        "https://media.gettyimages.com/id/123/photo/kimchi-stew.jpg",
        "https://www.istockphoto.com/photo/example.jpg",
    ]

    for url in blocked_urls:
        assert searcher.validate_image_url(url) is False

