"""Description parsers. Google's live page is a script wall; the parser must ignore that."""

from app.services.describe import clip_sentences, google_snippet, titles_match


def test_google_script_wall_is_not_a_description():
    html = "<html><body><noscript>Please click here if you are not redirected</noscript><script>enablejs</script></body></html>"
    assert google_snippet(html) is None


def test_google_snippet_is_kept_when_the_panel_is_present():
    html = '<div class="kno-rdesc"><span>Apple Inc. is an American technology company. It sells the iPhone.</span></div>'
    text = google_snippet(html)
    assert text is not None
    assert text.startswith("Apple Inc. is an American technology company.")


def test_wikipedia_title_must_share_a_name_token():
    assert titles_match("Apple Inc.", "Apple Inc.")
    assert titles_match("Tencent Holdings Limited", "Tencent")
    assert not titles_match("Apple Inc.", "Apricot")


def test_clip_keeps_two_sentences():
    text = "First sentence. Second sentence. Third sentence that should be dropped."
    assert clip_sentences(text) == "First sentence. Second sentence."
