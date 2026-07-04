# Gmail Thread Exporter

This project provides an automated way to extract **all emails (including full conversation threads)** from Gmail for a specific email address using the **Gmail API**.

---

## 🚀 Features

* Fetch complete **email threads**, not just individual messages
* Filter emails by a **specific email ID**
* Supports Gmail-style search queries (`from:`, `to:`, `cc:`, etc.)
* Handles pagination (large inboxes)
* Outputs structured data in **JSON format**
* Works with multiple Google accounts

---

## 🛠️ Setup

### 1. Enable Gmail API

1. Go to: https://console.cloud.google.com/
2. Create or select a project
3. Enable **Gmail API**
4. Go to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth Client ID**
6. Select:

   > ✅ **Desktop App**
7. Download the file and save it as:

   ```
   credentials.json
   ```

---

### 2. Install Dependencies

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

---

### 3. First Run (Authentication)

Run the script:

```bash
python export_gmail_threads.py --email person@example.com
```

* A browser window will open
* Select the Google account you want to use
* Grant permissions

A file called `token.json` will be created:

* This stores your login session
* Future runs will reuse this account automatically

---

## 📌 Usage

### Basic Usage

```bash
python export_gmail_threads.py --email person@example.com
```

This fetches all threads where the email appears in:

* From
* To
* CC
* BCC

---

### Advanced Query

```bash
python export_gmail_threads.py --query 'from:"person@example.com"'
```

You can use Gmail search operators:

* `from:`
* `to:`
* `cc:`
* `bcc:`
* `subject:`
* `has:attachment`
* `{ }` for OR conditions

---

### Include Spam & Trash

```bash
python export_gmail_threads.py --email person@example.com --include-spam-trash
```

---

### Output File

```bash
python export_gmail_threads.py --email person@example.com --output data.json
```

---

## 📂 Output Format

The script exports data in JSON:

```json
[
  {
    "threadId": "12345",
    "messageCount": 2,
    "messages": [
      {
        "from": "example@gmail.com",
        "to": "user@gmail.com",
        "subject": "Hello",
        "date": "...",
        "plainBody": "...",
        "htmlBody": "...",
        "attachments": []
      }
    ]
  }
]
```

---

## 👤 Multiple Account Support

The script uses the account linked to `token.json`.

### Switch Accounts

```bash
rm token.json
```

Re-run the script and choose a different account.

---

### Use Multiple Accounts (Recommended)

Modify the script:

```python
TOKEN_FILE = "token_work.json"
```

Create separate token files:

* `token_personal.json`
* `token_work.json`

---

## 🔍 Verify Which Account Is Used

Add this snippet:

```python
profile = service.users().getProfile(userId="me").execute()
print("Fetching from:", profile["emailAddress"])
```

---

## ⚠️ Common Errors

### ❌ Error 400: redirect_uri_mismatch

**Cause:** Wrong OAuth client type

**Fix:**

* Use **Desktop App**, not Web Application
* Delete old `credentials.json`
* Delete `token.json`
* Re-authenticate

---

## 🔒 Permissions

This app uses:

```
https://www.googleapis.com/auth/gmail.readonly
```

It only reads your emails and does not modify anything.

---

## 📎 Notes

* Threads are returned if **any message in the thread matches the query**
* Large mailboxes may take time due to API pagination
* Attachments metadata is included (not downloaded)

---

## 📈 Future Improvements

* Export to CSV / Excel
* Download attachments
* Save emails as `.eml` files
* Add date range filters
* UI interface

---

## 🧑‍💻 Author

Built for automated Gmail data extraction using official Google APIs.

---
