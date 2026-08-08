"""Build the repository's short, credential-free product demo video."""

from pathlib import Path
from io import BytesIO
import struct

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = ROOT / "docs" / "screenshots"
OUTPUT = ROOT / "docs" / "demo" / "sentinel-ai-demo.avi"
WIDTH, HEIGHT, FPS = 1280, 720, 15


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def title_frame(title: str, subtitle: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#06111d")
    draw = ImageDraw.Draw(image)
    draw.ellipse((740, -280, 1420, 400), fill="#192056")
    draw.ellipse((-250, 420, 480, 1100), fill="#063b4b")
    draw.text((90, 215), title, font=font(62, True), fill="#f5f8ff")
    draw.text((94, 305), subtitle, font=font(27), fill="#7ee7ff")
    draw.text((94, 625), "SENTINEL AI  •  SECURE BUSINESS INTELLIGENCE", font=font(18, True), fill="#8093ab")
    return image


def fit(image_path: Path) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    image.thumbnail((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#030a12")
    canvas.paste(image, ((WIDTH - image.width) // 2, (HEIGHT - image.height) // 2))
    return canvas


def frames():
    scenes = [
        (title_frame("Sentinel AI", "A real dataset-to-decision workflow"), 2.0),
        (fit(SCREENSHOTS / "demo-login.png"), 3.0),
        (title_frame("Secure dataset onboarding", "Importing test6.csv • 30,000 tenant-isolated records"), 1.5),
        (fit(SCREENSHOTS / "demo-upload.png"), 3.0),
        (title_frame("Executive intelligence", "Live KPIs and charts generated from test6.csv"), 1.5),
        (fit(SCREENSHOTS / "demo-dashboard.png"), 4.0),
        (title_frame("Ask Sentinel AI", "Exact calculations backed by uploaded business data"), 1.5),
        (fit(SCREENSHOTS / "demo-sentinel-answer.png"), 3.5),
        (fit(SCREENSHOTS / "demo-sentinel-risk.png"), 4.0),
        (title_frame("From data to decisions", "Upload • Analyze • Ask Sentinel • Export PDF"), 2.0),
    ]
    fade = 12
    previous = None
    for scene, seconds in scenes:
        if previous is not None:
            for step in range(1, fade + 1):
                yield Image.blend(previous, scene, step / fade)
        for _ in range(max(1, int(seconds * FPS) - fade)):
            yield scene
        previous = scene


def chunk(name: bytes, data: bytes) -> bytes:
    return name + struct.pack("<I", len(data)) + data + (b"\0" if len(data) % 2 else b"")


def list_chunk(name: bytes, data: bytes) -> bytes:
    return chunk(b"LIST", name + data)


def encode_jpeg(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=82, optimize=True)
    return buffer.getvalue()


def write_mjpeg_avi(images: list[Image.Image]) -> None:
    encoded = [encode_jpeg(image) for image in images]
    largest = max(map(len, encoded))
    frame_count = len(encoded)
    avih = struct.pack(
        "<IIIIIIIIII4I", 1_000_000 // FPS, largest * FPS, 0, 0x10,
        frame_count, 0, 1, largest, WIDTH, HEIGHT, 0, 0, 0, 0,
    )
    strh = struct.pack(
        "<4s4sIHHIIIIIIIIhhhh", b"vids", b"MJPG", 0, 0, 0, 0, 1, FPS,
        0, frame_count, largest, 0xFFFFFFFF, 0, 0, 0, WIDTH, HEIGHT,
    )
    strf = struct.pack(
        "<IiiHH4sIiiII", 40, WIDTH, HEIGHT, 1, 24, b"MJPG", largest, 0, 0, 0, 0,
    )
    hdrl = list_chunk(b"hdrl", chunk(b"avih", avih) + list_chunk(b"strl", chunk(b"strh", strh) + chunk(b"strf", strf)))
    movi_data = bytearray()
    index = bytearray()
    offset = 4
    for jpeg in encoded:
        frame_chunk = chunk(b"00dc", jpeg)
        movi_data.extend(frame_chunk)
        index.extend(struct.pack("<4sIII", b"00dc", 0x10, offset, len(jpeg)))
        offset += len(frame_chunk)
    body = b"AVI " + hdrl + list_chunk(b"movi", bytes(movi_data)) + chunk(b"idx1", bytes(index))
    OUTPUT.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    write_mjpeg_avi(list(frames()))
    print(OUTPUT)


if __name__ == "__main__":
    main()
