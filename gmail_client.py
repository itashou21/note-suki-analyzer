"""
Gmail APIクライアント（公開版）
credentials.jsonをアップロードして使用
"""

import json
import base64
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Gmail APIのスコープ（読み取り専用）
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailClient:
    def __init__(self, credentials_json=None):
        self.service = None
        self.creds = None
        self.credentials_json = credentials_json

    def get_auth_url(self, redirect_uri="urn:ietf:wg:oauth:2.0:oob"):
        """認証URLを取得"""
        if not self.credentials_json:
            raise ValueError("credentials.jsonが設定されていません")

        flow = Flow.from_client_config(
            self.credentials_json,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        auth_url, _ = flow.authorization_url(prompt='consent')
        return auth_url, flow

    def authenticate_with_code(self, flow, code):
        """認証コードでトークンを取得"""
        flow.fetch_token(code=code)
        self.creds = flow.credentials
        self.service = build('gmail', 'v1', credentials=self.creds)
        return True

    def get_note_suki_emails(self, max_results=500):
        """noteからのスキ通知メールを取得する"""
        if not self.service:
            raise Exception("認証が完了していません")

        # noteからのスキ通知メールを検索
        query = 'from:note.com subject:スキされました'

        emails = []
        page_token = None

        while len(emails) < max_results:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(100, max_results - len(emails)),
                pageToken=page_token
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                break

            for msg in messages:
                email_data = self._get_email_detail(msg['id'])
                if email_data:
                    emails.append(email_data)

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        return emails

    def _get_email_detail(self, msg_id):
        """メールの詳細を取得する"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            headers = message['payload']['headers']

            subject = None
            date = None

            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'Date':
                    date = header['value']

            # 日時をパース（日本時間に変換）
            received_at = None
            if date:
                try:
                    dt = parsedate_to_datetime(date)
                    jst = timezone(timedelta(hours=9))
                    received_at = dt.astimezone(jst)
                except:
                    pass

            # 本文を取得
            body = self._get_email_body(message['payload'])

            # 記事タイトルを抽出
            article_title = self._extract_article_title(subject, body)

            return {
                'id': msg_id,
                'subject': subject,
                'received_at': received_at,
                'article_title': article_title,
                'body': body
            }
        except Exception as e:
            print(f"Error getting email {msg_id}: {e}")
            return None

    def _get_email_body(self, payload):
        """メール本文を取得する"""
        body = ""

        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

        body = self._strip_html(body)
        return body

    def _strip_html(self, html):
        """HTMLタグを除去してテキストを抽出"""
        import re
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<[^>]+>', '\n', html)
        html = html.replace('&nbsp;', ' ')
        html = html.replace('&amp;', '&')
        html = html.replace('&lt;', '<')
        html = html.replace('&gt;', '>')
        html = html.replace('&quot;', '"')
        html = re.sub(r'\n\s*\n', '\n', html)
        return html.strip()

    def _extract_article_title(self, subject, body):
        """メールから記事タイトルを抽出する"""
        import re

        if not body:
            return "不明な記事"

        lines = body.strip().split('\n')

        found_marker = False
        for line in lines:
            line = line.strip()

            if '作品が読者に届いています' in line:
                found_marker = True
                continue

            if found_marker and line and len(line) > 3:
                if any(skip in line for skip in [
                    'スキとは', 'スキしてくれた人', 'http', '@', '配信停止',
                    'スキされました', 'スキしました', 'ヘルプ', 'プライバシー'
                ]):
                    continue

                if 'さんにスキされました' in line:
                    continue

                title = self._clean_title(line)
                if title and len(title) > 3:
                    return title[:100]

        return "不明な記事"

    def _clean_title(self, title):
        """タイトルから不要な部分を除去"""
        import re
        title = re.sub(r'は\d+スキを突破しました.*', '', title)
        title = re.sub(r'が\d+スキを突破しました.*', '', title)
        title = re.sub(r'\s*[（(]\s*\d+\s*スキ\s*[）)]', '', title)
        title = re.sub(r'\s*\(\d+スキ\)', '', title)
        title = re.sub(r'\s*（\d+スキ）', '', title)
        title = re.sub(r'[♥❤]\s*\d+', '', title)
        title = re.sub(r'SHO\s*[|｜].*', '', title)
        title = re.sub(r'さんにスキされました.*', '', title)
        title = re.sub(r'[\s　!！]+$', '', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip()
