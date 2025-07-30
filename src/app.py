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
    # 🚀 AIが加速させる、未来の特許探索 - PatentFinder 3.2
    PatentFinder 3.2は、あなたのアイデアを未来の技術に繋げる、次世代のAIパートナーです。
    そのプロセスは、3つのシンプルなステップで、驚くほどの結果をもたらします。
    """)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### **Step 1: 自然な言葉で技術内容を入力**
        探したい技術やアイデアを、普段使っている自然な言葉で入力します。
        > **バックグラウンドでの処理内容:**
        > 入力された文は、**大規模言語モデル（LLM）**によって処理されます。これは、言葉の意味や文脈を理解するAI技術であり、利用者の意図を読み取る役割を担います。
        """)
    with col2:
        st.markdown("""
        ### **Step 2: AIが検索条件を構築**
        AIは、入力された内容に基づき、検索に必要な条件を自動的に推定・生成します。
        1.  **LLMによるIPC・キーワードの推定**
            入力内容から関連する**IPC（国際特許分類）**や、検索に有効なキーワード群をAIが推定します。
        2.  **LLMによるSQL文の自動生成とデータベース検索**
            AIが設定したIPCやキーワードを基に、巨大な特許データベース（BigQuery）を効率よく検索するための、**高精度な検索命令（SQL）**を自動で作成します。
        """)
    with col3:
        st.markdown("""
        ### **Step 3: AIが「意味の近さ」で情報を賢く厳選する**
        検索で得られた大量の特許情報も、AIがさらにひと手間加えて、あなたに届けます。
        > **舞台裏のテクノロジー:**
        > **Embedding（エンベディング）**という技術を使い、言葉や文章が持つ「意味」を、コンピュータが計算できる数値データ（**ベクトル**）に変換します。
        AIは、あなたの最初の質問と、見つかった特許一つひとつの「意味（ベクトル）」を比較計算します。そして、意味的に最も近い、つまり**あなたの意図に最も関連性の高い特許から順番に**並べ替えて提示します。
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

