"""
noteスキ分析 Webアプリ（公開版）
credentials.jsonをアップロードして使用
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

from gmail_client import GmailClient
from analyzer import SukiAnalyzer

# ページ設定
st.set_page_config(
    page_title="noteスキ分析",
    page_icon="❤️",
    layout="wide"
)

# セッション状態の初期化
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'emails' not in st.session_state:
    st.session_state.emails = []
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = None
if 'credentials_json' not in st.session_state:
    st.session_state.credentials_json = None
if 'auth_flow' not in st.session_state:
    st.session_state.auth_flow = None


def main():
    st.title("❤️ noteスキ分析ツール")
    st.markdown("Gmailに届いたnoteのスキ通知を分析して、いつスキが押されたかを可視化します。")

    # タブで使い方と分析を切り替え
    if not st.session_state.authenticated:
        tab1, tab2 = st.tabs(["🔐 認証・分析", "📖 使い方ガイド"])

        with tab2:
            show_usage_guide()

        with tab1:
            pass  # 認証セクションは下で表示

    # サイドバー
    with st.sidebar:
        st.header("設定")

        if st.session_state.authenticated:
            st.success("✅ Gmail認証済み")
            if st.button("最初からやり直す"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        elif st.session_state.credentials_json:
            st.info("📄 credentials.json アップロード済み")
        else:
            st.warning("⚠️ credentials.jsonをアップロードしてください")

        st.markdown("---")
        st.markdown("""
        ### 使い方
        1. Google Cloud Consoleで認証情報を作成
        2. credentials.jsonをアップロード
        3. 認証URLにアクセスしてコードを取得
        4. コードを入力して認証完了
        5. メールを取得して分析開始
        """)

        st.markdown("---")
        st.markdown("""
        ### セキュリティについて
        - アップロードしたファイルはサーバーに保存されません
        - セッション終了時にすべてのデータが削除されます
        - このツールはGmailの読み取り専用アクセスのみ要求します
        """)

    # メインコンテンツ
    if not st.session_state.authenticated:
        show_auth_section()
    else:
        show_analysis_section()


def show_usage_guide():
    """使い方ガイドを表示"""
    st.header("📖 使い方ガイド")

    st.markdown("""
    このツールは、Gmailに届いたnoteのスキ通知メールを分析して、
    **いつスキが押されたか**を可視化するWebアプリです。
    """)

    st.subheader("✨ 機能")
    st.markdown("""
    - 📧 Gmailからスキ通知メールを自動取得
    - 📊 記事ごとのスキ数を集計
    - ⏱️ 投稿後の時間分布を分析（24時間以内 / 1-3日後 / 3-7日後 / 1週間以降）
    - 📈 スキの累積推移グラフ
    - 🕐 時間帯別分布（何時にスキが押されやすいか）
    """)

    st.subheader("🔧 事前準備（初回のみ）")
    st.markdown("""
    このツールを使うには、Google Cloud Consoleで認証情報を作成する必要があります。
    **約10分程度で完了します。**
    """)

    with st.expander("📝 ステップ1: Google Cloud プロジェクト作成", expanded=True):
        st.markdown("""
        1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
        2. Googleアカウントでログイン
        3. 画面上部の「プロジェクトを選択」→「新しいプロジェクト」をクリック
        4. プロジェクト名を入力（例: `note-suki-analyzer`）して作成
        """)

    with st.expander("📝 ステップ2: Gmail APIを有効化"):
        st.markdown("""
        1. 左メニュー「APIとサービス」→「ライブラリ」
        2. 検索欄に「Gmail API」と入力
        3. Gmail APIをクリックし、「有効にする」ボタンを押す
        """)

    with st.expander("📝 ステップ3: OAuth同意画面を設定"):
        st.markdown("""
        1. 左メニュー「APIとサービス」→「OAuth同意画面」
        2. User Type：「外部」を選択して「作成」
        3. アプリ名を入力（例: `noteスキ分析`）
        4. ユーザーサポートメール：自分のメールアドレス
        5. デベロッパー連絡先：自分のメールアドレス
        6. 「保存して次へ」を押していく
        7. **テストユーザー**の画面で「ADD USERS」→ **自分のGmailアドレスを追加**
        8. 「保存して次へ」で完了
        """)

    with st.expander("📝 ステップ4: 認証情報（credentials.json）を作成"):
        st.markdown("""
        1. 左メニュー「APIとサービス」→「認証情報」
        2. 「＋認証情報を作成」→「OAuthクライアントID」
        3. アプリケーションの種類：「**デスクトップアプリ**」を選択
        4. 名前を入力して「作成」
        5. 「**JSONをダウンロード**」をクリック
        6. ダウンロードしたファイルが `credentials.json` です
        """)

    st.subheader("🚀 ツールの使い方")
    st.markdown("""
    1. 「認証・分析」タブに移動
    2. ダウンロードした `credentials.json` をアップロード
    3. 「認証URLを取得」をクリック
    4. 表示されたURLにアクセスし、Googleアカウントで認証
    5. 表示された認証コードをコピーしてツールに貼り付け
    6. 「スキ通知メールを取得」で分析開始！
    """)

    st.subheader("🔒 セキュリティについて")
    st.info("""
    - アップロードしたcredentials.jsonはサーバーに保存されません
    - セッション終了時（ブラウザを閉じた時）にすべてのデータが削除されます
    - Gmail APIは**読み取り専用**アクセスのみ要求します
    - メールの内容が外部に送信されることはありません
    """)

    st.subheader("💬 作者")
    st.markdown("""
    **SHO** | AI副業365日検証チャレンジ

    noteで毎日AIを活用した副業検証の記録を投稿しています。
    """)


def show_auth_section():
    """認証セクション"""
    st.header("🔐 Gmail認証")

    # ステップ1: credentials.jsonのアップロード
    st.subheader("ステップ1: credentials.jsonをアップロード")

    if not st.session_state.credentials_json:
        with st.expander("📖 credentials.jsonの作成方法", expanded=False):
            st.markdown("""
            1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
            2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
            3. 「APIとサービス」→「ライブラリ」→「Gmail API」を検索して有効化
            4. 「APIとサービス」→「OAuth同意画面」を設定
               - User Type: 外部
               - テストユーザーに自分のGmailを追加
            5. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」
            6. アプリケーションの種類：「デスクトップアプリ」
            7. 作成後、「JSONをダウンロード」をクリック
            """)

        uploaded_file = st.file_uploader(
            "credentials.jsonをアップロード",
            type=['json'],
            help="Google Cloud Consoleからダウンロードしたファイル"
        )

        if uploaded_file:
            try:
                credentials_json = json.load(uploaded_file)
                st.session_state.credentials_json = credentials_json
                st.success("✅ credentials.jsonを読み込みました！")
                st.rerun()
            except Exception as e:
                st.error(f"ファイルの読み込みに失敗しました: {e}")
        return

    st.success("✅ credentials.json アップロード済み")

    # ステップ2: 認証URLの取得
    st.subheader("ステップ2: Googleで認証")

    if not st.session_state.auth_flow:
        if st.button("🔗 認証URLを取得", type="primary"):
            try:
                client = GmailClient(st.session_state.credentials_json)
                auth_url, flow = client.get_auth_url()
                st.session_state.auth_flow = flow
                st.session_state.auth_url = auth_url
                st.rerun()
            except Exception as e:
                st.error(f"エラー: {e}")
        return

    st.markdown("**以下のURLにアクセスして、Googleアカウントで認証してください：**")
    st.code(st.session_state.auth_url)
    st.markdown("認証後に表示される**コード**をコピーしてください。")

    # ステップ3: 認証コードの入力
    st.subheader("ステップ3: 認証コードを入力")

    auth_code = st.text_input(
        "認証コード",
        placeholder="4/0AY0e-g7...",
        help="Googleの認証画面で表示されたコードを貼り付けてください"
    )

    if st.button("✅ 認証を完了", type="primary"):
        if not auth_code:
            st.error("認証コードを入力してください")
            return

        with st.spinner("認証中..."):
            try:
                client = GmailClient(st.session_state.credentials_json)
                client.authenticate_with_code(st.session_state.auth_flow, auth_code)
                st.session_state.authenticated = True
                st.session_state.gmail_client = client
                st.success("✅ 認証成功！")
                st.rerun()
            except Exception as e:
                st.error(f"認証エラー: {e}")


def show_analysis_section():
    """分析セクション"""

    # メール取得
    if not st.session_state.emails:
        st.header("📧 メール取得")

        max_results = st.slider("取得するメール数", 50, 1000, 500, 50)

        if st.button("📥 スキ通知メールを取得", type="primary"):
            with st.spinner("メールを取得中...（時間がかかる場合があります）"):
                try:
                    client = st.session_state.gmail_client
                    emails = client.get_note_suki_emails(max_results=max_results)
                    st.session_state.emails = emails
                    st.session_state.analyzer = SukiAnalyzer(emails)
                    st.success(f"✅ {len(emails)}件のスキ通知を取得しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"取得エラー: {e}")
        return

    # 分析表示
    analyzer = st.session_state.analyzer

    # 全体統計
    st.header("📊 全体統計")
    stats = analyzer.get_overall_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("総スキ数", stats['total_emails'])
    with col2:
        st.metric("記事数", stats['unique_articles'])
    with col3:
        st.metric("平均スキ/記事", f"{stats['avg_suki_per_article']:.1f}")
    with col4:
        date_range = stats['date_range']
        days = (date_range['end'] - date_range['start']).days
        st.metric("分析期間", f"{days}日間")

    st.markdown("---")

    # 記事別分析
    st.header("📝 記事別分析")

    articles = analyzer.get_article_list()

    if articles:
        article_titles = [a['article_title'] for a in articles]
        selected_article = st.selectbox(
            "分析する記事を選択",
            article_titles,
            format_func=lambda x: f"{x} ({next((a['suki_count'] for a in articles if a['article_title'] == x), 0)}スキ)"
        )

        if selected_article:
            show_article_analysis(analyzer, selected_article, articles)

    # データ再取得ボタン
    st.markdown("---")
    if st.button("🔄 データを再取得"):
        st.session_state.emails = []
        st.session_state.analyzer = None
        st.rerun()


def show_article_analysis(analyzer, article_title, articles):
    """記事の詳細分析を表示"""

    article_info = next((a for a in articles if a['article_title'] == article_title), None)

    if not article_info:
        return

    st.subheader(f"「{article_title}」の分析")

    st.markdown("**投稿日時を入力すると、投稿後の経過時間で分析できます**")

    col1, col2 = st.columns(2)
    with col1:
        post_date = st.date_input(
            "投稿日",
            value=article_info['first_suki'].date() if article_info['first_suki'] else None
        )
    with col2:
        post_time = st.time_input("投稿時刻", value=datetime.strptime("20:00", "%H:%M").time())

    post_datetime = None
    if post_date and post_time:
        post_datetime = datetime.combine(post_date, post_time)

    analysis = analyzer.analyze_article(article_title, post_datetime)

    if not analysis:
        st.warning("データがありません")
        return

    # 基本統計
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総スキ数", analysis['total_suki'])
    with col2:
        st.metric("最初のスキ", analysis['first_suki'].strftime("%m/%d %H:%M"))
    with col3:
        st.metric("最後のスキ", analysis['last_suki'].strftime("%m/%d %H:%M"))

    # 投稿後の時間分布
    if 'time_distribution' in analysis and analysis['time_distribution']:
        st.markdown("### ⏱️ 投稿後の時間分布")

        dist = analysis['time_distribution']
        total = sum(dist.values())

        dist_with_pct = {k: {'count': v, 'pct': v/total*100 if total > 0 else 0} for k, v in dist.items()}

        fig = go.Figure(data=[
            go.Bar(
                x=list(dist.keys()),
                y=list(dist.values()),
                text=[f"{v}件 ({dist_with_pct[k]['pct']:.1f}%)" for k, v in dist.items()],
                textposition='auto',
                marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
            )
        ])
        fig.update_layout(
            title="いつスキが押されたか？",
            xaxis_title="投稿からの経過時間",
            yaxis_title="スキ数",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 💡 分析結果")
        immediate = dist.get('24時間以内', 0)
        later = sum(v for k, v in dist.items() if k != '24時間以内')
        immediate_pct = immediate / total * 100 if total > 0 else 0
        later_pct = later / total * 100 if total > 0 else 0

        st.info(f"""
        - **24時間以内**: {immediate}件 ({immediate_pct:.1f}%)
        - **それ以降**: {later}件 ({later_pct:.1f}%)

        → {'すぐにスキを押す読者が多いです' if immediate_pct > 70 else 'じっくり読んでからスキを押す読者が一定数います！'}
        """)

    # スキの累積グラフ
    st.markdown("### 📈 スキの累積推移")
    timeline = analyzer.get_suki_timeline(article_title)

    if timeline:
        df_timeline = pd.DataFrame(timeline)
        fig = px.line(
            df_timeline,
            x='received_at',
            y='cumulative_suki',
            markers=True
        )
        fig.update_layout(
            title="スキの累積推移",
            xaxis_title="日時",
            yaxis_title="累積スキ数"
        )
        st.plotly_chart(fig, use_container_width=True)

    # 時間帯別分布
    st.markdown("### 🕐 時間帯別分布（1日の中で）")
    hourly = analysis.get('hourly_distribution', {})
    if hourly:
        all_hours = {h: hourly.get(h, 0) for h in range(24)}
        fig = px.bar(
            x=list(all_hours.keys()),
            y=list(all_hours.values()),
            labels={'x': '時間', 'y': 'スキ数'}
        )
        fig.update_layout(title="何時にスキが押されやすいか？")
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
