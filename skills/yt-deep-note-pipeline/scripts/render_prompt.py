#!/usr/bin/env python3
import argparse
import datetime as dt
from pathlib import Path


PLACEHOLDERS = [
    "SOURCE_TYPE",
    "SOURCE_VALUE",
    "VIDEO_TITLE",
    "CHANNEL_NAME",
    "PUBLISH_DATE",
    "DURATION",
    "TRANSCRIPT_WITH_TIMESTAMPS",
    "NOTE_ID",
    "TODAY",
    "YYYY",
    "DATE_SLUG",
    "DURATION_SECONDS",
    "NOW_ISO8601",
    "NOW_TAIPEI",
]


def render_template(template: str, values: dict[str, str]) -> str:
    out = template
    for key in PLACEHOLDERS:
        out = out.replace(f"{{{{{key}}}}}", values.get(key, ""))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render YT deep note prompt template with runtime values."
    )
    parser.add_argument("--template", required=True, help="Path to template markdown.")
    parser.add_argument("--source-type", required=True, choices=["youtube", "mp4"])
    parser.add_argument("--source-value", required=True)
    parser.add_argument("--video-title", default="未命名影片")
    parser.add_argument("--channel-name", default="未知頻道")
    parser.add_argument("--publish-date", default="未知日期")
    parser.add_argument("--duration", default="未知長度")
    parser.add_argument("--duration-seconds", type=int, default=0)
    parser.add_argument("--note-id", default="note-auto")
    parser.add_argument("--date-slug", default="video-note")
    parser.add_argument("--transcript-file", help="Transcript text file with timestamps.")
    parser.add_argument("--out", help="Output prompt path. Print stdout if omitted.")
    args = parser.parse_args()

    now_utc = dt.datetime.now(dt.timezone.utc)
    now_taipei = now_utc.astimezone(dt.timezone(dt.timedelta(hours=8)))
    today = now_taipei.date().isoformat()
    yyyy = str(now_taipei.year)

    transcript = ""
    if args.transcript_file:
        transcript = Path(args.transcript_file).read_text(encoding="utf-8")

    values = {
        "SOURCE_TYPE": args.source_type,
        "SOURCE_VALUE": args.source_value,
        "VIDEO_TITLE": args.video_title,
        "CHANNEL_NAME": args.channel_name,
        "PUBLISH_DATE": args.publish_date,
        "DURATION": args.duration,
        "TRANSCRIPT_WITH_TIMESTAMPS": transcript,
        "NOTE_ID": args.note_id,
        "TODAY": today,
        "YYYY": yyyy,
        "DATE_SLUG": args.date_slug,
        "DURATION_SECONDS": str(args.duration_seconds),
        "NOW_ISO8601": now_utc.replace(microsecond=0).isoformat(),
        "NOW_TAIPEI": now_taipei.strftime("%Y-%m-%d %H:%M:%S %z"),
    }

    template_text = Path(args.template).read_text(encoding="utf-8")
    rendered = render_template(template_text, values)

    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
