import marimo

__generated_with = "0.11.31"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import requests
    import re
    import datetime
    import json
    return datetime, json, mo, re, requests


@app.cell
def _(mo):
    mo.md(
        r"""
        # Blue Sky Posting Tool

        First, what is your handle?

        No @ at the start, and the full thing (this probably includes ".bsky.social" at the end)
        """
    )
    return


@app.cell
def _(mo):
    bluesky_handle = mo.ui.text()
    bluesky_handle
    return (bluesky_handle,)


@app.cell
def _(mo):
    mo.md(r"""Ok, now we need an App password. Go to "Settings", "Privacy and Security" and "App Passwords". Create a new one and put it in below.""")
    return


@app.cell
def _(mo):
    bluesky_app_password = mo.ui.text()
    bluesky_app_password
    return (bluesky_app_password,)


@app.cell
def _(mo):
    mo.md(r"""Now what do you want to post? It should have at least one link in it.""")
    return


@app.cell
def _(mo):
    post_content  = mo.ui.text_area()
    post_content
    return (post_content,)


@app.cell
def _(mo):
    mo.md(
        r"""
        This is how many characters your post uses out of the allowed 300:

        (This only updates when you move the cursor out of the content box)
        """
    )
    return


@app.cell
def _(mo, post_content):
    mo.show_code(str(len(post_content.value)))
    return


@app.cell
def _(mo):
    mo.md(r"""For the first link in the post, what should the title of the preview be?""")
    return


@app.cell
def _(mo):
    preview_title = mo.ui.text()
    preview_title
    return (preview_title,)


@app.cell
def _(mo):
    mo.md("""For the first link in the post, what should the title of the description be?""")
    return


@app.cell
def _(mo):
    preview_description  = mo.ui.text_area()
    preview_description
    return (preview_description,)


@app.cell
def _(mo):
    mo.md("""For the first link in the post, what is the URL of the image that should be attached?""")
    return


@app.cell
def _(mo):
    preview_image_url  = mo.ui.text(value="https://bsky.app/static/social-card-default-gradient.png", full_width=True)
    preview_image_url
    return (preview_image_url,)


@app.cell
def _(mo):
    mo.md(r"""Now press the button to post this!""")
    return


@app.cell
def _(mo):
    go_button = mo.ui.run_button(label="Post Please")
    go_button
    return (go_button,)


@app.cell
def _(mo):
    mo.md("""Nothing happens here when you press the button - go and check your profile!""")
    return


@app.cell
def _(
    bluesky_app_password,
    bluesky_handle,
    datetime,
    go_button,
    json,
    mo,
    post_content,
    preview_description,
    preview_image_url,
    preview_title,
    re,
    requests,
):
    # Much code from https://docs.bsky.app/blog/create-post - thanks!

    def parse_urls(text: str):
        spans = []
        # partial/naive URL regex based on: https://stackoverflow.com/a/3809435
        # tweaked to disallow some training punctuation
        url_regex = rb"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
        text_bytes = text.encode("UTF-8")
        for m in re.finditer(url_regex, text_bytes):
            spans.append({
                "start": m.start(1),
                "end": m.end(1),
                "url": m.group(1).decode("UTF-8"),
            })
        return spans

    def parse_mentions(text: str):
        spans = []
        # regex based on: https://atproto.com/specs/handle#handle-identifier-syntax
        mention_regex = rb"[$|\W](@([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)"
        text_bytes = text.encode("UTF-8")
        for m in re.finditer(mention_regex, text_bytes):
            spans.append({
                "start": m.start(1),
                "end": m.end(1),
                "handle": m.group(1)[1:].decode("UTF-8")
            })
        return spans

    def parse_facets(text: str):
        facets = []
        for m in parse_mentions(text):
            resp = requests.get(
                "https://bsky.social/xrpc/com.atproto.identity.resolveHandle",
                params={"handle": m["handle"]},
            )
            # If the handle can't be resolved, just skip it!
            # It will be rendered as text in the post instead of a link
            if resp.status_code == 400:
                continue
            did = resp.json()["did"]
            facets.append({
                "index": {
                    "byteStart": m["start"],
                    "byteEnd": m["end"],
                },
                "features": [{"$type": "app.bsky.richtext.facet#mention", "did": did}],
            })
        for u in parse_urls(text):
            facets.append({
                "index": {
                    "byteStart": u["start"],
                    "byteEnd": u["end"],
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        # NOTE: URI ("I") not URL ("L")
                        "uri": u["url"],
                    }
                ],
            })
        return facets

    if go_button.value:
        # Get Token
        resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": bluesky_handle.value, "password": bluesky_app_password.value},
        )
        resp.raise_for_status()
        session = resp.json()
        bluesky_token = session["accessJwt"]
        bluesky_did = session["did"]
    
        # Image
        resp = requests.get(preview_image_url.value or "")
        resp.raise_for_status()

        blob_resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Content-Type": resp.headers.get('content-type', '').lower(),
                "Authorization": "Bearer " + bluesky_token,
            },
            data=resp.content,
        )
        blob_resp.raise_for_status()
        image_blob = blob_resp.json()["blob"]
    
        # Make the post!
        now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        urls = parse_urls(post_content.value)
        post = {
            "$type": "app.bsky.feed.post",
            "text": post_content.value,
            "createdAt": now,
            "embed": {
                "$type": "app.bsky.embed.external",
                "external": {
                    "uri": urls[0]["url"],
                    "title": preview_title.value,
                    "description": preview_description.value,
                    "thumb": image_blob
                }
            },
            "facets": parse_facets(post_content.value)        
        }

        resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": "Bearer " + bluesky_token},
            json={
                "repo": bluesky_did,
                "collection": "app.bsky.feed.post",
                "record": post,
            },
        )
        resp.raise_for_status()
        mo.show_code(json.dumps(resp.json(), indent=2))
    
    return (
        blob_resp,
        bluesky_did,
        bluesky_token,
        image_blob,
        now,
        parse_facets,
        parse_mentions,
        parse_urls,
        post,
        resp,
        session,
        urls,
    )


if __name__ == "__main__":
    app.run()
