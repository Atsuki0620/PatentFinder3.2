import streamlit as st
from core.state import AppState
from ui import sidebar, main_view

# --- ページ設定 ---
st.set_page_config(
    page_title="PatentFinder 3.2",
    layout="wide"
)

# --- 状態管理 ---
if 'app_state' not in st.session_state:
    st.session_state.app_state = AppState()
if 'show_landing_page' not in st.session_state:
    st.session_state.show_landing_page = True

app_state: AppState = st.session_state.app_state

# --- UIコンポーネント ---
def show_landing_page():
    """トップページ（ランディングページ）を表示する"""
    st.markdown("""
    # 🔍 AIを活用した特許探索支援ツール - PatentFinder 3.2
    PatentFinder 3.2は、大規模言語モデル（LLM）とGoogleの特許データベースを活用し、自然言語での入力から特許情報の抽出、分析、可視化までを支援する特許探索ツールです。
    以下の4ステップで調査を進めることができます。
    """)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### **Step 1: LLMとの対話による検索条件の生成**
        自然な言葉で調査したい技術や課題を入力します。

        - **文の意図の理解**  
          大規模言語モデル（LLM）が入力文を解析し、調査の目的を把握します。

        - **IPC分類・キーワードの推定**  
          内容に応じて、関連するIPC（国際特許分類）やキーワードをLLMが自動で推定します。

        - **調査テーマの再構成**  
          入力文をもとに、検索の軸となる調査テーマを提示します。
        """)
    with col2:
        st.markdown("""
        ### **Step 2: Googleデータベースによる検索の実行**
        推定された検索条件をもとに、Googleの特許データベースから情報を抽出します。

        - **検索SQLの自動生成**  
          推定されたIPCやキーワードに基づき、LLMがBigQuery用のSQL（Structured Query Language）を自動生成します。

        - **BigQueryによる検索処理**  
          作成されたSQLを用いて、Googleの特許データベース（BigQuery）から関連文献を取得します。
        """)
    with col3:
        st.markdown("""
        ### **Step 3: 検索結果の出力とスコアリング**
        検索で得られた特許情報に対して、意味的な関連度をスコア化して並べ替えます。

        - **Embeddingによるベクトル化**  
          タイトル・要約文・調査テーマをベクトル空間に写像します。

        - **コサイン類似度によるスコアリング**  
          調査テーマと各特許文献とのコサイン類似度（ベクトルの内積）を計算し、関連度を定量評価します。

        - **関連性順での並び替え**  
          コサイン類似度が高い順に特許をソートし、表示します。
        """)

    st.markdown("---")
    st.markdown("""
    ### **Step 4: パテントマップの作成とピンポイント評価**
    出力された検索結果をもとに、さらに深掘りと分析を進めることが可能です。

    - **パテントマップの生成**  
      出現頻度や技術分類などをもとに、検索結果を可視化します。

    - **重点特許の抽出・評価**  
      スコアの高い文献に注目し、個別に内容を確認・精査することで、調査対象の技術的背景や位置づけを把握できます。
    """)

    st.markdown("---")

    st.markdown("##### PatentFinder 3.2は、特許探索を「作業」から「発見」へと進化させます。さあ、AIと共に、未来を創るアイデア探しの旅へ。")

    if st.button("▶ 今すぐ始める", type="primary"):
        st.session_state.show_landing_page = False
        st.rerun()


def show_main_app():
    """メインアプリケーションのUIを表示する"""
    sidebar.show()
    main_view.show(app_state)


# --- メインロジック ---
if st.session_state.show_landing_page:
    show_landing_page()
else:
    show_main_app()

