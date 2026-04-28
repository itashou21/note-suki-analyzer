"""
スキ通知メールの分析ロジック
"""

import pandas as pd
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import re

# 日本時間
JST = timezone(timedelta(hours=9))

class SukiAnalyzer:
    def __init__(self, emails):
        """
        emails: GmailClientから取得したメールのリスト
        """
        self.emails = emails
        self.df = self._create_dataframe()

    def _create_dataframe(self):
        """メールデータをDataFrameに変換"""
        data = []
        for email in self.emails:
            if email['received_at']:
                data.append({
                    'received_at': email['received_at'],
                    'article_title': email['article_title'],
                    'subject': email['subject']
                })

        df = pd.DataFrame(data)
        if not df.empty:
            # 既にJSTに変換済みなのでそのまま使用
            df['received_at'] = pd.to_datetime(df['received_at'])
            df['date'] = df['received_at'].dt.date
            df['hour'] = df['received_at'].dt.hour
            df['weekday'] = df['received_at'].dt.day_name()

        return df

    def get_article_list(self):
        """記事一覧を取得"""
        if self.df.empty:
            return []

        articles = self.df.groupby('article_title').agg({
            'received_at': ['count', 'min', 'max']
        }).reset_index()

        articles.columns = ['article_title', 'suki_count', 'first_suki', 'last_suki']
        articles = articles.sort_values('first_suki', ascending=False)

        return articles.to_dict('records')

    def analyze_article(self, article_title, post_datetime=None):
        """
        特定の記事のスキ分析を行う

        article_title: 記事タイトル
        post_datetime: 記事の投稿日時（指定すると投稿からの経過時間で分析）
        """
        article_df = self.df[self.df['article_title'] == article_title].copy()

        if article_df.empty:
            return None

        result = {
            'article_title': article_title,
            'total_suki': len(article_df),
            'first_suki': article_df['received_at'].min(),
            'last_suki': article_df['received_at'].max(),
        }

        # 投稿日時が指定されている場合、経過時間で分析
        if post_datetime:
            # JSTタイムゾーンを付与
            post_dt = pd.to_datetime(post_datetime).tz_localize(JST)
            article_df['hours_after_post'] = (
                article_df['received_at'] - post_dt
            ).dt.total_seconds() / 3600

            # 時間帯別の分布
            result['time_distribution'] = self._calc_time_distribution(article_df)

        # 時間帯別（1日の中で）
        result['hourly_distribution'] = article_df.groupby('hour').size().to_dict()

        # 曜日別
        result['weekday_distribution'] = article_df.groupby('weekday').size().to_dict()

        return result

    def _calc_time_distribution(self, df):
        """投稿後の時間分布を計算"""
        if 'hours_after_post' not in df.columns:
            return {}

        distribution = {
            '24時間以内': len(df[df['hours_after_post'] <= 24]),
            '1-3日後': len(df[(df['hours_after_post'] > 24) & (df['hours_after_post'] <= 72)]),
            '3-7日後': len(df[(df['hours_after_post'] > 72) & (df['hours_after_post'] <= 168)]),
            '1週間以降': len(df[df['hours_after_post'] > 168]),
        }

        return distribution

    def get_overall_stats(self):
        """全体の統計を取得"""
        if self.df.empty:
            return {}

        return {
            'total_emails': len(self.df),
            'unique_articles': self.df['article_title'].nunique(),
            'date_range': {
                'start': self.df['received_at'].min(),
                'end': self.df['received_at'].max()
            },
            'avg_suki_per_article': len(self.df) / self.df['article_title'].nunique()
        }

    def get_suki_timeline(self, article_title):
        """記事のスキのタイムラインを取得"""
        article_df = self.df[self.df['article_title'] == article_title].copy()

        if article_df.empty:
            return []

        article_df = article_df.sort_values('received_at')
        article_df['cumulative_suki'] = range(1, len(article_df) + 1)

        return article_df[['received_at', 'cumulative_suki']].to_dict('records')
