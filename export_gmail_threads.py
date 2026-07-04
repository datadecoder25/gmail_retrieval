import argparse
import base64
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import csv
import html
import re
from email.utils import parseaddr

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def extract_email(address):
    if not address:
        return ""
    return parseaddr(address)[1].lower()

def get_service():
    creds = None
    if Path("token.json").exists():
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        Path("token.json").write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def decode_b64url(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def html_to_text(html_body: str) -> str:
    if not html_body:
        return ""
    text = re.sub(r"(?is)<script.*?>.*?</script>", "", html_body)
    text = re.sub(r"(?is)<style.*?>.*?</style>", "", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p>|</div>|</li>", "\n", text)
    text = re.sub(r"(?is)<li>", "- ", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = text.strip()
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    normalized = " ".join(lines)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def headers_to_dict(headers):
    out = {}
    for h in headers or []:
        name = h.get("name", "").lower()
        value = h.get("value", "")
        if name:
            out[name] = value
    return out


def walk_parts(part, plain_parts, html_parts, attachments):
    mime = part.get("mimeType", "")
    body = part.get("body", {}) or {}
    filename = part.get("filename", "")
    data = body.get("data")

    if filename:
        attachments.append(
            {
                "filename": filename,
                "mimeType": mime,
                "attachmentId": body.get("attachmentId"),
                "size": body.get("size"),
            }
        )

    # Avoid treating attached files as message body
    if not filename and data:
        if mime == "text/plain":
            plain_parts.append(decode_b64url(data))
        elif mime == "text/html":
            html_parts.append(decode_b64url(data))

    for child in part.get("parts", []) or []:
        walk_parts(child, plain_parts, html_parts, attachments)


def list_thread_ids(service, query, include_spam_trash=False):
    thread_ids = []
    page_token = None

    while True:
        resp = (
            service.users()
            .threads()
            .list(
                userId="me",
                q=query,
                includeSpamTrash=include_spam_trash,
                maxResults=500,
                pageToken=page_token,
            )
            .execute()
        )

        thread_ids.extend(t["id"] for t in resp.get("threads", []))
        page_token = resp.get("nextPageToken")

        if not page_token:
            break

    return thread_ids


def export_threads(service, thread_ids):
    exported = []

    for i, thread_id in enumerate(thread_ids, start=1):
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )

        out_messages = []
        for msg in thread.get("messages", []):
            payload = msg.get("payload", {}) or {}
            headers = headers_to_dict(payload.get("headers", []))
            plain_parts, html_parts, attachments = [], [], []

            walk_parts(payload, plain_parts, html_parts, attachments)

            out_messages.append(
                {
                    "id": msg.get("id"),
                    "threadId": msg.get("threadId"),
                    "internalDate": msg.get("internalDate"),
                    "labelIds": msg.get("labelIds", []),
                    "snippet": msg.get("snippet", ""),
                    "from": headers.get("from", ""),
                    "to": headers.get("to", ""),
                    "cc": headers.get("cc", ""),
                    "bcc": headers.get("bcc", ""),
                    "subject": headers.get("subject", ""),
                    "date": headers.get("date", ""),
                    "plainBody": "\n".join(p for p in plain_parts if p).strip(),
                    "htmlBody": "\n".join(p for p in html_parts if p).strip(),
                    "attachments": attachments,
                }
            )

        exported.append(
            {
                "threadId": thread.get("id"),
                "snippet": thread.get("snippet", ""),
                "messageCount": len(out_messages),
                "messages": out_messages,
            }
        )

        print(f"[{i}/{len(thread_ids)}] exported thread {thread_id}")

    return exported

def export_csv(exported_threads, output_csv):
    print("export_csv called")
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        writer.writerow([
            "thread_id",
            "subject",
            "senders",
            "message_count",
            "thread"
        ])

        for thread in exported_threads:

            messages = sorted(
                thread["messages"],
                key=lambda x: int(x["internalDate"])
            )

            sender_set = set()
            conversation = []

            for msg in messages:
                sender = extract_email(msg["from"])
                if sender:
                    sender_set.add(sender)

                raw_body = msg["plainBody"] or html_to_text(msg["htmlBody"])
                body = normalize_text(raw_body)
                if body:
                    conversation.append(body)

            writer.writerow([
                thread["threadId"],
                normalize_text(messages[0]["subject"]) if messages else "",
                "; ".join(sorted(sender_set)),
                len(messages),
                " \n ".join(conversation)
            ])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Target email address")
    parser.add_argument(
        "--query",
        help='Optional full Gmail query. Overrides --email. Example: from:"person@example.com"',
    )
    parser.add_argument("--output", default="gmail_threads.json")
    parser.add_argument(
        "--csv-output",
        default="output.csv",
        help="CSV output path. Defaults to the JSON output filename with .csv extension.",
    )
    parser.add_argument("--include-spam-trash", action="store_true")
    args = parser.parse_args()

    # Default: any thread where this address appears in from/to/cc/bcc
    query = args.query or (
        f'{{from:"{args.email}" to:"{args.email}" '
        f'cc:"{args.email}" bcc:"{args.email}"}}'
    )

    print("Using query:", query)

    service = get_service()
    thread_ids = list_thread_ids(
        service, query=query, include_spam_trash=args.include_spam_trash
    )
    print(f"Found {len(thread_ids)} matching thread(s).")

    data = export_threads(service, thread_ids)
    csv_output = Path(args.csv_output) if args.csv_output else Path(args.output).with_suffix(".csv")
    export_csv(data, csv_output)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved JSON to {args.output}")
    print(f"Saved CSV to {csv_output}")


if __name__ == "__main__":
    main()