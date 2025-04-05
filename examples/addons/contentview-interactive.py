from mitmproxy import contentviews


class InteractiveSwapCase(contentviews.InteractiveContentview):
    def prettify(
        self,
        data: bytes,
        metadata: contentviews.Metadata,
    ) -> str:
        return data.swapcase().decode()

    def reencode(
        self,
        prettified: str,
        metadata: contentviews.Metadata,
    ) -> bytes:
        return prettified.encode().swapcase()


contentviews.add(InteractiveSwapCase)
