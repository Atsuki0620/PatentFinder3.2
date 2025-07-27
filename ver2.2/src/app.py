import streamlit as st
import pandas as pd
import os
from utils.config import load_env, setup_api_keys
from core.state import AppState
from core.agent import run_interaction, execute_patent_search_workflow, run_summary_workflow

# 環境変数の読み込み
load_env()

# --- ページ設定 ---
st.set_page_config(
    page_title="PatentsFinder2.2 - Conversational",
    page_icon=" patent:",
    layout="wide",
)

# --- 状態管理 ---
if 'app_state' not in st.session_state:
    st.session_state.app_state = AppState()
app_state: AppState = st.session_state.app_state

# --- サイドバー ---
with st.sidebar:
    st.title("APIキー設定")
    openai_api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    gcp_sa_json_str = st.text_area("GCP Service Account JSON", placeholder='{\n  "type": "service_account",\n  ...\n}')
    
    if st.button("APIキーを設定"):
        setup_api_keys(openai_api_key, gcp_sa_json_str)

    st.divider()

    st.title("表示設定")
    # 表示言語選択UI
    app_state.display_language = st.radio(
        "表示言語を選択",
        ("ja", "en"),
        index=0 if app_state.display_language == "ja" else 1,
        format_func=lambda x: "日本語" if x == "ja" else "English"
    )

# --- メイン画面 ---
st.title("PatentsFinder2.2 - 対話型特許検索")

if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    st.warning("APIキーが設定されていません。サイドバーから入力・設定してください。")
    st.stop()

# --- UIレイアウト ---
col1, col2 = st.columns(2)

with col1:
    st.header("1. AIと対話して検索条件を作成")
    
    # 対話履歴の表示
    chat_container = st.container()
    with chat_container:
        for author, message in app_state.chat_history:
            with st.chat_message(author):
                st.markdown(message)

    # ユーザーからの入力
    if prompt := st.chat_input("調査したい技術内容をどうぞ（例：AIを使った自動運転技術）"):
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        app_state.chat_history.append(("user", prompt))
        
        # AIを呼び出し、対話または条件生成を実行
        with st.spinner("AIが応答を生成中..."):
            updated_state = run_interaction(app_state)
            st.session_state.app_state = updated_state
        st.rerun()

with col2:
    st.header("2. 調査方針の確認・編集")
    app_state.plan_text = st.text_area(
        "調査方針（自動生成）",
        value=app_state.plan_text or "",
        height=200
    )

    if st.button("この方針で検索条件を生成", disabled=not app_state.plan_text):
        with st.spinner("検索条件を生成中..."):
            # 検索条件生成のロジックを直接呼び出す
            from core.agent import generate_query
            st.session_state.app_state = generate_query(app_state)
        st.rerun()

    st.header("3. 検索条件の確認・編集")
    
    # キーワード
    app_state.search_query.keywords = st.text_area(
        "キーワード", 
        value="\n".join(app_state.search_query.keywords),
        height=150
    ).splitlines()
    
    # IPCコード
    current_ipc_codes_str = "\n".join(app_state.search_query.ipc_codes)
    edited_ipc_codes_str = st.text_area(
        "IPCコード", 
        value=current_ipc_codes_str,
        height=150
    )
    new_ipc_codes = []
    for line in edited_ipc_codes_str.splitlines():
        line = line.strip()
        if not line:
            continue
        new_ipc_codes.append(line)
    app_state.search_query.ipc_codes = new_ipc_codes

    # 詳細条件
    with st.expander("詳細条件（任意）"):
        app_state.search_query.publication_date_from = st.text_input("公開日（From: YYYYMMDD）", value=app_state.search_query.publication_date_from or "")
        app_state.search_query.publication_date_to = st.text_input("公開日（To: YYYYMMDD）", value=app_state.search_query.publication_date_to or "")
        app_state.search_query.limit = st.number_input("検索件数の上限 (LIMIT)", min_value=1, max_value=1000, value=app_state.search_query.limit)

# --- 検索実行と結果表示 --- 
st.header("4. 検索実行")
if st.button("検索開始", type="primary"):
    if not app_state.search_query.keywords and not app_state.search_query.ipc_codes:
        st.error("キーワードまたはIPCコードを少なくとも1つは設定してください。")
    else:
        with st.spinner("特許検索ワークフローを実行中..."):
            st.session_state.app_state = execute_patent_search_workflow(app_state)
        st.success("検索が完了しました。")
        st.rerun()

# ワークフローとSQLの可視化
st.subheader("ワークフローとSQLの可視化")
col_wf, col_sql = st.columns(2)
with col_wf:
    with st.expander("エージェントワークフロー", expanded=False):
        if app_state.agent_node_graph:
            st.graphviz_chart(app_state.agent_node_graph)
        else:
            st.info("ワークフローはまだ開始されていません。")
with col_sql:
    with st.expander("生成されたSQLと解説", expanded=False):
        if app_state.generated_sql:
            st.markdown(f"**SQL解説:** {app_state.sql_explanation}")
            st.code(app_state.generated_sql, language="sql")
            st.markdown(f"**検索条件オブジェクト解説:** {app_state.search_query_explanation}")
        else:
            st.info("SQLはまだ生成されていません。")

# 類似度分析の仕組み表示
st.subheader("類似度分析の仕組み")
with st.expander("類似度分析の詳細と重み調整", expanded=False):
    st.markdown("特許検索結果は、入力された**調査方針**と各文献の**タイトル・要約・請求項**との類似度に基づいてスコアリングされます。")
    st.markdown("1. **Embedding化**: 調査方針と、各文献のセクション（タイトル等）をOpenAIの`text-embedding-3-small`でベクトル化します。")
    st.markdown("2. **類似度計算**: 調査方針のベクトルと、各セクションのベクトルとのコサイン類似度をそれぞれ計算します（`sim_title`, `sim_abstract`, `sim_claims`）。")
    st.markdown("3. **スコアリング**: 各類似度に重みを掛けて合計し、最終的なスコア（`score`）を算出します。スコアが高いほど、調査方針に合致していると判断されます。")
    
    st.markdown("**スコア計算式の重み調整:**")
    weights = app_state.similarity_weights
    w_title = st.slider("タイトル(title)の重み", 0.0, 1.0, weights.get('title', 0.4), 0.05)
    w_abstract = st.slider("要約(abstract)の重み", 0.0, 1.0, weights.get('abstract', 0.4), 0.05)
    w_claims = st.slider("請求項(claims)の重み", 0.0, 1.0, weights.get('claims', 0.2), 0.05)

    # 合計が1になるように正規化するオプション（ユーザーに委ねる）
    if st.checkbox("重みの合計を1に正規化する", value=True):
        total_weight = w_title + w_abstract + w_claims
        if total_weight > 0:
            w_title /= total_weight
            w_abstract /= total_weight
            w_claims /= total_weight
    
    app_state.similarity_weights = {"title": w_title, "abstract": w_abstract, "claims": w_claims}
    st.write(f"現在の重み: Title={w_title:.2f}, Abstract={w_abstract:.2f}, Claims={w_claims:.2f}")

# 結果表示エリア
st.header("5. 検索結果")
if app_state.analyzed_results is not None and not app_state.analyzed_results.empty:
    st.write(f"取得件数: {len(app_state.analyzed_results)}件")
    
    display_df = app_state.analyzed_results.copy()
    
    # スコア関連のカラムをフォーマット
    score_cols = ['score', 'sim_title', 'sim_abstract', 'sim_claims']
    for col in score_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].map(lambda x: f"{x:.3f}")

    if app_state.display_language == "ja":
        display_df = display_df.rename(columns={
            'title': 'タイトル',
            'abstract': '要約',
            'claims': '請求項',
            'assignee_harmonized': '出願人',
            'publication_date': '公開日',
            'ipc_codes': 'IPCコード',
            'score': 'スコア',
            'sim_title': 'タイトル類似度',
            'sim_abstract': '要約類似度',
            'sim_claims': '請求項類似度'
        })
    else: # en
        display_df = display_df.rename(columns={
            'title': 'Title',
            'abstract': 'Abstract',
            'claims': 'Claims',
            'assignee_harmonized': 'Assignee',
            'publication_date': 'Publication Date',
            'ipc_codes': 'IPC Codes',
            'score': 'Score',
            'sim_title': 'Title Similarity',
            'sim_abstract': 'Abstract Similarity',
            'sim_claims': 'Claims Similarity'
        })

    # 表示するカラムを選択
    display_columns = [
        col for col in display_df.columns 
        if col not in ['publication_number', 'select_for_summary'] # これらは後で使う
    ]

    # 編集可能なデータフレームで要約対象を選択
    df_to_show = display_df.copy()
    df_to_show["select_for_summary"] = False

    edited_df = st.data_editor(
        df_to_show,
        column_config={
            "select_for_summary": st.column_config.CheckboxColumn(
                "要約対象",
                default=False,
            )
        },
        use_container_width=True,
        hide_index=True,
        column_order=["select_for_summary"] + display_columns # チェックボックスを先頭に
    )
    
    selected_rows = edited_df[edited_df.select_for_summary]
    
    if not selected_rows.empty:
        st.write("選択された特許:")
        st.dataframe(selected_rows.drop(columns=['select_for_summary']))
        
        if st.button("選択した特許を要約"):
            with st.spinner("要約を生成中..."):
                app_state.selected_patents_for_summary = selected_rows['publication_number'].tolist()
                st.session_state.app_state = run_summary_workflow(app_state)
            st.success("要約が完了しました。")
            st.rerun()

    if app_state.summary_result:
        st.subheader("要約結果")
        st.markdown(app_state.summary_result)

elif app_state.error:
    st.error(app_state.error)
else:
    st.info("まだ検索は実行されていません。")