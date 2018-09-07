import pathlib
import shutil

src = pathlib.Path("../../net/data/verificationcerts")
here = pathlib.Path(".")

shutil.copy(src / "9da13359.0", "9da13359.0")

for x in ["self-signed", "trusted-leaf", "trusted-root"]:
    (here / f"{x}.pem").write_text(
        (src / f"{x}.crt").read_text() +
        (src / f"{x}.key").read_text()
    )
