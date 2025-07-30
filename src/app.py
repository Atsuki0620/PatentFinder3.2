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
        ### **Step 1: あなたの言葉が、分析の起点になる**
        まず、探したい技術やアイデアを、普段使っている自然な言葉で入力します。
        > **舞台裏のテクノロジー:**
        > ここでは**LLM（大規模言語モデル）**という、人間のように言葉を理解するAIが働いています。あなたの言葉に込められた意図を正確に読み取ることが、すべての始まりです。
        """)
    with col2:
        st.markdown("""
        ### **Step 2: AIが最適な「検索戦略」を自動で立案する**
        あなたの言葉を分析したAIは、専門家のような思考で、瞬時に2つの重要な処理を実行します。
        1.  **IPC・キーワードをAIが推定**
            あなたの入力内容から、関連性の高い技術分野を示す**IPC（国際特許分類）**や、専門家が使うような**効果的なキーワード群**をAIが自動で推測し、設定します。
        2.  **高精度な検索命令（SQL）を自動生成**
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

