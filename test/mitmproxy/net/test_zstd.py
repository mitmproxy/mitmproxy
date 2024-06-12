from mitmproxy.net.encoding import decode_zstd
from mitmproxy.net.encoding import encode_zstd


def test_zstd():

    FRAME_SIZE = 1024

    # Create payload of 1024b
    test_content = 'a' * FRAME_SIZE

    # Compress it, will result a single frame
    single_frame = encode_zstd(test_content.encode())

    # Concat compressed frame, it'll result two frames, total size of 2048b payload
    two_frames = single_frame + single_frame

    # Uncompressed single frame should have the size of FRAME_SIZE
    assert len(decode_zstd(single_frame)) == FRAME_SIZE

    # Uncompressed two frames should have the size of FRAME_SIZE * 2
    assert len(decode_zstd(two_frames)) == FRAME_SIZE * 2
