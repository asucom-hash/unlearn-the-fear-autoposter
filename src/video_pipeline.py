"""Render original Unlearn The Fear videos from licensed footage and scripts.

The renderer intentionally keeps the final MP4 out of git. GitHub Pages hosts
it only long enough for Instagram to ingest it, while Facebook and YouTube get
the local file directly. Source images are selected from licence-checked
Wikimedia Commons results; the finished edit, captions, script and ambient bed
are original to this project.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state" / "video_state.json"
QUOTE_PATH = ROOT / "quotes.json"
DOCS = ROOT / "docs"
WORK = ROOT / ".video-work"

GOLD = (234, 189, 100, 255)
WHITE = (249, 246, 235, 255)
BLACK = (7, 10, 18, 210)

TOPICS = (
    ("Courage", "mountain sunrise", "A brave next step"),
    ("Healing", "calm ocean sunrise", "Letting go with kindness"),
    ("Mindfulness", "misty forest sunlight", "Returning to the present"),
    ("Self-worth", "person walking nature", "Your worth is already here"),
    ("Presence", "quiet lake morning", "The life happening now"),
    ("Self-care", "warm window rain", "Rest is part of becoming"),
    ("Resilience", "mountain trail clouds", "Growing through uncertainty"),
    ("Relationships", "golden sunset people", "Choosing honest connection"),
    ("Hope", "sunrise landscape", "Making room for better days"),
    ("Gratitude", "wildflowers golden hour", "Noticing what is good"),
)

LONG_SHAPES = (
    {
        "title": "How to Take the Next Step When Fear Feels Loud",
        "theme": 0,
        "opening": "Fear often asks for a complete map before it allows us to move. But most meaningful changes begin before certainty arrives.",
        "practice": "Choose one action small enough to begin today: send the message, open the document, take the walk, or ask the question.",
    },
    {
        "title": "A Gentle Guide to Letting Go and Moving Forward",
        "theme": 1,
        "opening": "Letting go is not a decision to forget. It is a decision not to make an old pain the author of every new day.",
        "practice": "Name one thing you are ready to carry more lightly, then make a little room for what you would like life to hold instead.",
    },
    {
        "title": "How to Calm an Overthinking Mind",
        "theme": 2,
        "opening": "An anxious mind can make a possibility feel like a certainty. Calm begins when we return to what is true in this moment.",
        "practice": "Pause before answering the loudest thought. Take one slow breath, look around you, and name three things that are real and safe now.",
    },
    {
        "title": "Build Self-Worth Without Comparing Your Life",
        "theme": 3,
        "opening": "Comparison turns another person's visible chapter into a judgement of your unseen work. Your own life deserves your attention.",
        "practice": "Notice one piece of progress that would have been invisible to anyone else, and allow it to count.",
    },
    {
        "title": "The Quiet Power of Being Present",
        "theme": 4,
        "opening": "Life rarely pauses until every task is finished. Presence is how we stop postponing the moments that are already here.",
        "practice": "Give one ordinary moment your full attention today: a meal, a walk, a conversation, or the first quiet minute of the morning.",
    },
    {
        "title": "Why Rest Is Not Falling Behind",
        "theme": 5,
        "opening": "Rest is often mistaken for losing momentum. In truth, a rested mind is better able to choose a direction worth following.",
        "practice": "Protect one small pocket of rest this week, without trying to earn it first.",
    },
)


def run(args: list[str], *, cwd: Path | None = None) -> None:
    # Preserve ffmpeg diagnostics in the Actions log if a source file or codec
    # is rejected. Capturing them would hide the actual repair clue.
    subprocess.run(args, cwd=cwd, check=True)


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
    ).strip()
    return float(out)


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"next_short_quote": 24, "next_long_episode": 0, "short_history": [], "long_history": []}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def topic_for(index: int) -> tuple[str, str, str]:
    return TOPICS[(index // 18) % len(TOPICS)]


def short_transcript(quote: str, topic: str) -> str:
    return (
        f"Today's {topic.lower()} reminder. {quote} "
        "You do not have to solve your whole life in this moment. "
        "Let this be a small pause, a calmer breath, and one honest next step. "
        "Keep what helps you move forward, gently."
    )


def long_transcript(shape: dict, quotes: list[str]) -> str:
    """Build an original, themed guided reflection—not a quote slideshow."""
    bridges = (
        "This is not an instruction to ignore what is difficult. It is an invitation to meet it without handing it all the power.",
        "Notice how different this feels when you stop treating progress as a performance for other people.",
        "The point is not to get it perfect. The point is to make the next choice a little more honest and a little less fearful.",
        "You can take this slowly. A gentle change that lasts matters more than a dramatic promise that disappears tomorrow.",
        "When the mind argues back, return to what is practical: one breath, one boundary, one conversation, one small action.",
    )
    passages = [
        f"Welcome to Unlearn The Fear. {shape['opening']} This reflection is not about forcing yourself to feel positive. It is about making room for a steadier way forward.",
        "As you listen, keep only what feels useful. You do not have to agree with every sentence for one idea to become a useful companion today.",
    ]
    for number, quote in enumerate(quotes, start=1):
        bridge = bridges[(number + shape["theme"]) % len(bridges)]
        passages.append(
            f"Here is the next thought to sit with. {quote} {bridge} "
            "Try not to rush past that. Think of one ordinary moment in your own life where it could be true. "
            "Maybe the change is not visible yet. Maybe it is simply the way you speak to yourself, the permission you give yourself, or the choice you no longer postpone. "
            "That still counts."
        )
    passages.extend(
        [
            f"Before we finish, return to this simple practice: {shape['practice']} You are not late. You are learning how to take care of the life that is actually yours.",
            "Thank you for spending these minutes with Unlearn The Fear. Let go of fear, discover your strength, and live your life—one calm, meaningful choice at a time.",
        ]
    )
    return " ".join(passages)


def synthesize(text: str, output: Path, *, long_form: bool) -> None:
    """Generate local narration without a cloud key or usage bill.

    The default Piper voice is a public-domain English male model. The model
    is cached by the Actions workflow after its first download. Use
    PIPER_VOICE only for a voice whose model-card licence has been reviewed.
    """
    # Ryan is a fuller, more natural male voice than the original Norman
    # model.  A slightly longer phoneme scale keeps the delivery calm rather
    # than rushed without stretching or artificially pitching the audio.
    voice = os.getenv("PIPER_VOICE", "en_US-ryan-high")
    length_scale = float(os.getenv("PIPER_LENGTH_SCALE", "1.14"))
    if not 0.5 <= length_scale <= 2.0:
        raise ValueError("PIPER_LENGTH_SCALE must be between 0.5 and 2.0")
    data_dir = Path(os.getenv("PIPER_DATA_DIR", ROOT / ".piper-voices"))
    data_dir.mkdir(parents=True, exist_ok=True)
    wav = output.with_suffix(".wav")
    model = data_dir / f"{voice}.onnx"
    if not model.exists():
        run(["python", "-m", "piper.download_voices", "--data-dir", str(data_dir), voice])
    # Piper takes the complete script as an argument, avoiding a shell and
    # keeping punctuation intact for a calmer, more natural read.
    run([
        "python", "-m", "piper", "-m", voice, "--data-dir", str(data_dir),
        "--length-scale", f"{length_scale:.2f}", "-f", str(wav), "--", text,
    ])
    # Gentle low-end warmth makes the male narration sound less thin, while
    # preserving intelligibility on phone speakers.
    run([
        "ffmpeg", "-y", "-i", str(wav), "-af",
        "lowshelf=f=180:g=4,highshelf=f=4000:g=-2,acompressor=threshold=-18dB:ratio=2:attack=20:release=180",
        "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "192k", str(output),
    ])


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value or "")).strip()


def download_commons_image(query: str, choice: int, output: Path) -> dict:
    """Download a usable Commons thumbnail and return its required credit.

    New Pexels API key issuance is currently paused. Commons' public API lets
    us remain key-free, but we honour each source's attribution in the caption.
    Non-commercial and no-derivatives licences are explicitly rejected.
    """
    response = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query", "generator": "search", "gsrsearch": query,
            "gsrnamespace": 6, "gsrlimit": 20, "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 1280, "format": "json",
        },
        headers={"User-Agent": "UnlearnTheFearVideoBot/1.0 (educational motivational video pipeline)"},
        timeout=45,
    )
    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    pages = list(data.get("query", {}).get("pages", {}).values())
    permitted: list[tuple[dict, dict, str]] = []
    for page in pages:
        title = page.get("title", "")
        if not title.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licence = plain((meta.get("LicenseShortName") or {}).get("value", "")).lower()
        if not licence or "noncommercial" in licence or "non-free" in licence or "no derivatives" in licence:
            continue
        if not any(label in licence for label in ("public domain", "cc0", "cc by", "cc-by")):
            continue
        source_url = info.get("thumburl") or info.get("url")
        if source_url:
            permitted.append((page, info, licence))
    if not response.ok or not permitted:
        raise RuntimeError(f"No permitted Wikimedia Commons image was found for {query!r}")
    page, info, licence = permitted[choice % len(permitted)]
    media = requests.get(
        info.get("thumburl") or info["url"],
        stream=True,
        timeout=90,
        headers={"User-Agent": "UnlearnTheFearVideoBot/1.0 (educational motivational video pipeline)"},
    )
    media.raise_for_status()
    with output.open("wb") as handle:
        for chunk in media.iter_content(1024 * 1024):
            if chunk:
                handle.write(chunk)
    meta = info.get("extmetadata") or {}
    artist = plain((meta.get("Artist") or {}).get("value", "Wikimedia Commons contributor"))
    return {
        "title": page.get("title", "Wikimedia Commons image"),
        "creator": artist or "Wikimedia Commons contributor",
        "license": plain((meta.get("LicenseShortName") or {}).get("value", "")),
        "source": f"https://commons.wikimedia.org/?curid={page.get('pageid')}",
    }


def make_overlay(path: Path, title: str, quote: str | None, *, width: int, height: int) -> None:
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    scale = width / (1080 if height > width else 1920)
    regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", max(14, round((32 if height > width else 26) * scale)))
    bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(24, round((58 if height > width else 46) * scale)))
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(12, round((24 if height > width else 20) * scale)))
    draw.rectangle((0, 0, width, int(height * 0.14)), fill=(4, 7, 13, 135))
    draw.text((width // 2, int(height * 0.055)), "UNLEARN THE FEAR", anchor="mm", font=small, fill=GOLD)
    max_chars = 23 if height > width else 38
    title_lines = textwrap.wrap(title, width=max_chars)
    y = int(height * (0.23 if height > width else 0.19))
    for line in title_lines:
        draw.text((width // 2, y), line, anchor="mm", font=bold, fill=WHITE, stroke_width=2, stroke_fill=(0, 0, 0, 180))
        y += int(bold.size * 1.2)
    if quote:
        # Keep the persistent quote clear of the caption-safe area near the
        # lower edge of a vertical Short.
        box_top = int(height * (0.45 if height > width else 0.63))
        box_bottom = min(height - 115, box_top + int(height * (0.15 if height > width else 0.22)))
        draw.rounded_rectangle((int(width * 0.08), box_top, int(width * 0.92), box_bottom), radius=28, fill=BLACK)
        lines = textwrap.wrap(quote, width=30 if height > width else 54)
        y = box_top + 44
        for line in lines[:5]:
            draw.text((width // 2, y), line, anchor="mm", font=regular, fill=GOLD, stroke_width=1, stroke_fill=(0, 0, 0, 160))
            y += int(regular.size * 1.35)
    draw.text((width // 2, height - 58), "Let Go of Fear. Discover Your Strength. Live Your Life.", anchor="mm", font=regular, fill=WHITE, stroke_width=1, stroke_fill=(0, 0, 0, 150))
    im.save(path)


CAPTION_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "for",
    "from", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "with", "you", "your",
})


def ass_escape(value: str) -> str:
    """Escape text before placing it in an ASS subtitle dialogue line."""
    return value.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def caption_focus(sentence: str) -> tuple[int, int] | None:
    """Choose one meaningful word to colour lavender in a caption card."""
    candidates = [
        match for match in re.finditer(r"[A-Za-z][A-Za-z'-]*", sentence)
        if match.group(0).lower() not in CAPTION_STOP_WORDS
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda match: (len(match.group(0)), match.start()))
    return best.span()


def caption_rows(sentence: str, *, vertical: bool) -> list[str]:
    """Wrap captions inside a fixed text-safe width before rendering them."""
    return textwrap.wrap(
        sentence,
        width=32 if vertical else 54,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [sentence]


def emphasise_ass(sentence: str) -> str:
    focus = caption_focus(sentence)
    if not focus:
        return ass_escape(sentence)
    start, end = focus
    # Lavender foreground, then reset to the style's black text colour.
    return (
        f"{ass_escape(sentence[:start])}{{\\c&H00ED9CB7&}}"
        f"{ass_escape(sentence[start:end])}{{\\r}}{ass_escape(sentence[end:])}"
    )


def make_ass_captions(text: str, duration: float, output: Path, *, width: int, height: int) -> None:
    """Write high-contrast, in-frame caption cards for FFmpeg/libass."""
    sentences = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
    weights = [max(6, len(sentence.split())) for sentence in sentences]
    total = sum(weights) or 1
    cursor = 0.35
    vertical = height > width
    font_size = 48 if vertical else 38
    margin_lr = 88 if vertical else 130
    # This keeps a two-line caption card away from platform controls, even on
    # phones which crop or overlay the lower edge of a vertical video.
    margin_v = 390 if vertical else 120
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        # Opaque yellow card; black text; the one highlighted word is written
        # with an ASS inline lavender colour override below.
        f"Style: CaptionCard,DejaVu Sans,{font_size},&H00000000,&H00000000,&H004AD4F7,&H004AD4F7,-1,0,0,0,100,100,0,0,3,18,0,2,{margin_lr},{margin_lr},{margin_v},1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]

    def stamp(value: float) -> str:
        total_centis = int(round(value * 100))
        hours, total_centis = divmod(total_centis, 360_000)
        minutes, total_centis = divmod(total_centis, 6_000)
        seconds, centis = divmod(total_centis, 100)
        return f"{hours}:{minutes:02}:{seconds:02}.{centis:02}"

    for number, (sentence, weight) in enumerate(zip(sentences, weights), start=1):
        length = max(2.0, duration * weight / total)
        end = min(duration - 0.1, cursor + length)
        rows = caption_rows(sentence, vertical=vertical)
        caption = r"\N".join(emphasise_ass(row) for row in rows)
        lines.append(f"Dialogue: 0,{stamp(cursor)},{stamp(end)},CaptionCard,,0,0,0,,{caption}")
        cursor = end + 0.10
    output.write_text("\n".join(lines), encoding="utf-8")


def make_visual(clips: list[Path], output: Path, *, width: int, height: int, duration: float) -> None:
    segments: list[Path] = []
    per_clip = duration / len(clips)
    for i, clip in enumerate(clips):
        segment = WORK / f"segment-{i}.mp4"
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p,fade=t=in:st=0:d=0.7,fade=t=out:st={max(per_clip-0.7, 0):.2f}:d=0.7"
        if clip.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            source_args = ["-loop", "1", "-framerate", "30", "-i", str(clip)]
        else:
            source_args = ["-stream_loop", "-1", "-i", str(clip)]
        run(["ffmpeg", "-y", *source_args, "-t", f"{per_clip:.2f}", "-an", "-vf", vf, "-movflags", "+faststart", str(segment)])
        segments.append(segment)
    listing = WORK / "clips.txt"
    listing.write_text("".join(f"file '{path.name}'\n" for path in segments))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(output)], cwd=WORK)


def render_video(*, narration: Path, overlay: Path, output: Path, width: int, height: int, quote: str | None, clips: list[Path], seed: int) -> float:
    audio_duration = probe_duration(narration)
    duration = max(28.0, audio_duration + 1.4) if height > width else max(420.0, audio_duration + 2.0)
    visual = WORK / "visual.mp4"
    make_visual(clips, visual, width=width, height=height, duration=duration)
    subtitles = WORK / "captions.ass"
    make_ass_captions(CURRENT_TRANSCRIPT, duration, subtitles, width=width, height=height)
    # Generated sine-pad audio is original, avoids copyright claims, and stays
    # deliberately below the narration.
    chords = ((174.61, 261.63, 349.23), (146.83, 220.0, 293.66), (196.0, 246.94, 293.66), (130.81, 196.0, 261.63))
    root, third, fifth = chords[seed % len(chords)]
    ambient = f"0.018*sin(2*PI*{root}*t)+0.012*sin(2*PI*{third}*t)+0.008*sin(2*PI*{fifth}*t)"
    # The ASS file declares its canvas and generous safe margins itself, so
    # libass does not scale the caption card unexpectedly on a 9:16 Short.
    filter_graph = (
        f"[0:v][1:v]overlay=0:0,ass={subtitles.name}[v];"
        f"[2:a]volume=1[narration];[3:a]lowpass=f=1300,volume=0.17[bed];"
        "[narration][bed]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )
    run([
        "ffmpeg", "-y", "-i", str(visual), "-loop", "1", "-i", str(overlay), "-i", str(narration),
        "-f", "lavfi", "-t", f"{duration:.2f}", "-i", f"aevalsrc={ambient}:s=48000",
        "-filter_complex", filter_graph, "-map", "[v]", "-map", "[a]", "-t", f"{duration:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output),
    ], cwd=WORK)
    return duration


CURRENT_TRANSCRIPT = ""


def prepare(kind: str) -> dict:
    global CURRENT_TRANSCRIPT
    WORK.mkdir(exist_ok=True)
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir()
    state = load_state()
    bank = json.loads(QUOTE_PATH.read_text())
    key = f"pending_{kind}"
    pending = state.get(key)
    if kind == "short":
        if not pending:
            index = int(state.get("next_short_quote", 24))
            if index >= len(bank):
                raise RuntimeError("Video quote bank exhausted. Add original quotes before publishing another video.")
            topic, query, hook = topic_for(index)
            quote = bank[index]
            pending = {
                "quote_index": index,
                "quote": quote,
                "title": f"{hook} | A Daily Reminder",
                "caption": f"{hook}.\n\n“{quote}”\n\nA quiet reminder from Unlearn The Fear.\n\n#UnlearnTheFear #Mindset #Motivation #PersonalGrowth #InnerPeace",
                "video_path": f"reels/daily-{index+1:04d}.mp4",
                "topic": topic,
                "query": query,
                "youtube_id": None,
                "instagram_post_id": None,
                "facebook_post_id": None,
            }
            state[key] = pending
            save_state(state)
        transcript = short_transcript(pending["quote"], pending["topic"])
        width, height, queries = 1080, 1920, [pending["query"], "calm nature landscape"]
        output = DOCS / pending["video_path"]
        overlay_quote = pending["quote"]
    elif kind == "long":
        if not pending:
            episode = int(state.get("next_long_episode", 0))
            if episode >= len(LONG_SHAPES):
                raise RuntimeError("Long-form script queue exhausted. Add new original guided reflections before publishing another one.")
            shape = LONG_SHAPES[episode]
            start = shape["theme"] * 18
            quotes = [bank[start + (episode * 3 + n) % 18] for n in range(10)]
            pending = {
                "episode": episode,
                "title": shape["title"],
                "caption": f"{shape['title']} — an original guided reflection from Unlearn The Fear.\n\nLet Go of Fear. Discover Your Strength. Live Your Life.\n\n#UnlearnTheFear #Mindfulness #Motivation #PersonalGrowth",
                "video_path": f"long-form/episode-{episode+1:03d}.mp4",
                "trailer_path": f"reels/episode-{episode+1:03d}-trailer.mp4",
                "theme": shape["theme"],
                "youtube_id": None,
                "facebook_post_id": None,
                "instagram_post_id": None,
            }
            state[key] = pending
            save_state(state)
        shape = LONG_SHAPES[pending["episode"]]
        start = shape["theme"] * 18
        quotes = [bank[start + (pending["episode"] * 3 + n) % 18] for n in range(10)]
        transcript = long_transcript(shape, quotes)
        width, height, queries = 1920, 1080, ["mountain sunrise", "calm forest", "ocean horizon", "misty lake", "golden field", "walking in nature"]
        output = DOCS / pending["video_path"]
        overlay_quote = None
    else:
        raise ValueError("kind must be short or long")
    CURRENT_TRANSCRIPT = transcript
    output.parent.mkdir(parents=True, exist_ok=True)
    narration = WORK / "narration.mp3"
    synthesize(transcript, narration, long_form=kind == "long")
    orientation = "portrait" if height > width else "landscape"
    clips: list[Path] = []
    credits = []
    for pos, query in enumerate(queries):
        clip = WORK / f"source-{pos}.jpg"
        credits.append(download_commons_image(query, (pending.get("quote_index", pending.get("episode", 0)) * 7) + pos, clip))
        clips.append(clip)
    pending["visual_credits"] = credits
    overlay = WORK / "overlay.png"
    make_overlay(overlay, pending["title"], overlay_quote, width=width, height=height)
    seed = int(pending.get("quote_index", pending.get("episode", 0)))
    duration = render_video(narration=narration, overlay=overlay, output=output, width=width, height=height, quote=overlay_quote, clips=clips, seed=seed)
    if kind == "long":
        # Instagram receives a vertical trailer, not a poor horizontal repost.
        trailer_transcript = transcript.split(". ", 7)
        CURRENT_TRANSCRIPT = ". ".join(trailer_transcript[:8]) + ". Watch the full guided reflection on YouTube and Facebook."
        trailer_narration = WORK / "trailer.mp3"
        synthesize(CURRENT_TRANSCRIPT, trailer_narration, long_form=False)
        trailer_overlay = WORK / "trailer-overlay.png"
        make_overlay(trailer_overlay, "New guided reflection", shape["title"], width=1080, height=1920)
        trailer_output = DOCS / pending["trailer_path"]
        render_video(narration=trailer_narration, overlay=trailer_overlay, output=trailer_output, width=1080, height=1920, quote=shape["title"], clips=clips[:2], seed=seed + 1)
    pending["duration_seconds"] = round(duration, 1)
    save_state(state)
    print(json.dumps({"kind": kind, "output": str(output.relative_to(ROOT)), "duration_seconds": round(duration, 1), "title": pending["title"]}))
    return pending


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("short", "long"))
    prepare(parser.parse_args().kind)
