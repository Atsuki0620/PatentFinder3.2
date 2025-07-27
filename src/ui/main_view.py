import streamlit as st
from core.state import AppState
from core import agent, visualize
from datetime import date, timedelta
import pandas as pd

def show(app_state: AppState):
    """メイン画面の3カラムレイアウトを表示する"""

    if not st.session_state.get("openai_api_key_configured"):
        st.warning("サイドバーからAPIキーを設定してください。")
        st.stop()

    col1, col2, col3 = st.columns(3)

    # --- 左カラム: 対話 ---
    with col1:
        st.header("1. 対話")
        chat_container = st.container(height=500)
        with chat_container:
            for author, message in app_state.chat_history:
                with st.chat_message(name=author):
                    st.markdown(message)
        
        if prompt := st.chat_input("調査したい技術内容を入力..."):
            app_state.chat_history.append(("user", prompt))
            st.session_state.app_state = agent.run_initial_interaction(app_state)
            st.rerun()

    # --- 中央カラム: 検索条件 ---
    with col2:
        st.header("2. 検索条件")
        
        if app_state.proposed_plans and not app_state.plan_text:
            with st.container(border=True):
                st.markdown("**調査テーマの絞り込み**")
                st.write("ご関心に最も近い調査テーマを選択してください。")
                selected_plan = st.radio("調査テーマ候補:", options=app_state.proposed_plans, label_visibility="collapsed")
                if st.button("このテーマで進める", type="primary"):
                    app_state.plan_text = selected_plan
                    st.session_state.app_state = agent.suggest_search_terms(app_state)
                    st.rerun()

        if app_state.terms_suggested:
            st.info(f"""**確定した調査テーマ:**

{app_state.plan_text}""")
            
            with st.expander("詳細検索条件", expanded=True):
                today = date.today()
                five_years_ago = today - timedelta(days=5*365)
                app_state.search_conditions.start_date = st.date_input("From", value=five_years_ago)
                app_state.search_conditions.end_date = st.date_input("To", value=today)
                app_state.search_conditions.countries = st.multiselect("対象国", options=['US', 'JP', 'EP', 'WO', 'CN'], default=['US', 'JP', 'EP', 'WO', 'CN'])
                app_state.search_conditions.limit = st.number_input("取得件数", min_value=10, max_value=500, value=100, step=10)

            tab1, tab2 = st.tabs(["検索ターム", "生成されたSQL"])
            with tab1:
                st.subheader("主語")
                app_state.search_conditions.subject_keywords = st.multiselect("キーワード（主語）", options=list(set(app_state.search_conditions.subject_keywords)), default=app_state.search_conditions.subject_keywords)
                app_state.search_conditions.subject_ipc = st.multiselect("IPC（主語）", options=list(set(app_state.search_conditions.subject_ipc)), default=app_state.search_conditions.subject_ipc)
                st.subheader("述語")
                app_state.search_conditions.predicate_keywords = st.multiselect("キーワード（述語）", options=list(set(app_state.search_conditions.predicate_keywords)), default=app_state.search_conditions.predicate_keywords)
                app_state.search_conditions.predicate_ipc = st.multiselect("IPC（述語）", options=list(set(app_state.search_conditions.predicate_ipc)), default=app_state.search_conditions.predicate_ipc)
            with tab2:
                with st.expander("生成されたSQLクエリを見る"):
                    st.code(app_state.generated_sql or "検索実行時に生成されます。", language="sql")
        
        if app_state.terms_suggested:
            st.button(
                "検索実行", 
                type="primary", 
                use_container_width=True,
                on_click=agent.run_search_callback
            )

    # --- 右カラム: 結果と分析 ---
    with col3:
        st.header("3. 結果と分析")
        
        if app_state.error_message:
            st.error(app_state.error_message)

        tab1, tab2, tab3 = st.tabs(["検索結果", "分析", "レポート"])
        with tab1:
            if not app_state.search_results.empty:
                display_df = app_state.search_results.copy()
                if 'similarity' in display_df.columns:
                    display_df['similarity'] = display_df['similarity'].map(lambda x: f"{x:.1%}")
                
                # レポート対象を選択
                selected_numbers = st.multiselect(
                    "レポートに含める特許を選択してください:",
                    options=display_df['publication_number'].tolist()
                )
                
                st.dataframe(display_df)

            else:
                st.info("まだ検索は実行されていません。")
        with tab2:
            if not app_state.search_results.empty:
                st.plotly_chart(visualize.plot_publication_trend(app_state.search_results), use_container_width=True)
                st.plotly_chart(visualize.plot_assignee_ranking(app_state.search_results), use_container_width=True)
            else:
                st.info("グラフを表示するには、まず検索を実行してください。")
        with tab3:
            if st.button("選択した特許でレポートを生成", disabled=not app_state.search_results.empty):
                selected_patents_df = app_state.search_results[app_state.search_results['publication_number'].isin(selected_numbers)]
                
                # 選択された行を渡すようにagentを呼び出す
                # この部分はagent側の修正も必要になる
                # temp_app_state = app_state
                # temp_app_state.search_results["select_for_report"] = temp_app_state.search_results['publication_number'].isin(selected_numbers)
                # st.session_state.app_state = agent.run_report_generation(temp_app_state)
                
                st.warning("レポート生成ロジックを一時的に無効化しています。")
                # st.rerun()

            if app_state.report_text:
                st.markdown(app_state.report_text)
                st.download_button(
                    label="レポートをMarkdown形式でダウンロード",
                    data=app_state.report_text,
                    file_name="patent_summary_report.md",
                    mime="text/markdown",
                )
            else:
                st.info("検索結果テーブルで特許を選択し、「レポートを生成」ボタンを押してください。")



