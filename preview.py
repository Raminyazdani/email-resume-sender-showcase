"""Build a local, reviewable résumé email from a fictional application."""

import argparse
import json
import os
import re
import tempfile
from email.headerregistry import Address
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path


def field(record, key):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    if not value.isprintable():
        raise ValueError(f"{key} must be a single line of printable text")
    return value.strip()


def mailbox(record, name_key, address_key):
    name = field(record, name_key)
    raw_address = field(record, address_key)
    local_part, separator, domain = raw_address.partition("@")
    if not separator or domain.lower() != "example.org" or not re.fullmatch(
        r"[A-Za-z0-9_+-]+(?:\.[A-Za-z0-9_+-]+)*", local_part
    ):
        raise ValueError(f"{address_key} must be a simple mailbox at example.org")
    return Address(display_name=name, username=local_part, domain="example.org")


def build_preview(record_path, resume_path):
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("the application record must be a JSON object")

    sender = mailbox(record, "applicant", "from_email")
    recipient = mailbox(record, "contact", "to_email")
    role = field(record, "role")
    organization = field(record, "organization")
    work_sample = field(record, "work_sample")
    resume = resume_path.read_bytes()
    if not resume.decode("utf-8").strip():
        raise ValueError("the résumé must contain UTF-8 text")

    message = EmailMessage(policy=SMTP)
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = f"Application for {role}"
    message.set_content(
        f"Hello {recipient.display_name},\n\n"
        f"I am applying for the {role} role at {organization}. "
        f"{work_sample}\n\n"
        f"I have attached my résumé for review.\n\n"
        f"Best,\n{sender.display_name}\n"
    )
    message.add_attachment(
        resume,
        maintype="text",
        subtype="plain",
        filename="resume.txt",
        params={"charset": "utf-8"},
    )
    return message


def save_preview(message, output):
    payload = message.as_bytes()
    staging = tempfile.NamedTemporaryFile(dir=output.parent, delete=False)
    staging_path = Path(staging.name)
    try:
        with staging:
            staging.write(payload)
        os.link(staging_path, output)
    finally:
        staging_path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="UTF-8 JSON application record")
    parser.add_argument("resume", type=Path, help="UTF-8 plain-text résumé")
    parser.add_argument("--out", type=Path, required=True, help="new local .eml path")
    args = parser.parse_args()
    try:
        message = build_preview(args.record, args.resume)
        save_preview(message, args.out)
    except FileExistsError:
        parser.exit(1, f"Preview already exists: {args.out}\n")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Preview failed: {exc}\n")
    print(f"To: {message['To']}\nSubject: {message['Subject']}")
    print(f"Dry run saved to {args.out}")


if __name__ == "__main__":
    main()
