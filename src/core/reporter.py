import streamlit as st
import pandas as pd
from openai import OpenAI

GENERATE_REPORT_PROMPT = """
あなたは優秀な特許アナリストです。
以下の調査方針と、それに基づいて収集された特許リストを分析し、プロフェッショナルな調査サマリーレポートを作成してください。

# 調査方針
{plan}

# 特許リスト
{patent_list_text}

# レポート構成
レポートは以下の構成で、Markdown形式で記述してください。

## 1. 総括
調査方針に対して、収集された特許群全体から何が言えるかを簡潔にまとめてください。

## 2. 主要な技術動向
特許群から読み取れる技術的な傾向やアプローチを、箇条書きで3〜5点挙げてください。

## 3. 注目すべき特許
特に重要だと思われる特許を2〜3件ピックアップし、それぞれの特許番号と、その発明がなぜ注目に値するのかを簡潔に説明してください。

## 4. 主要プレイヤー
特許を多く出願している主要な企業や研究機関（出願人）を挙げ、その動向について考察してください。
"""

def generate_summary_report(plan: str, selected_patents: pd.DataFrame) -> str:
    """
    選択された特許情報に基づき、LLMにサマリーレポートを生成させる。
    """
    if selected_patents.empty:
        return "レポートを生成する特許が選択されていません。"

    try:
        client = OpenAI(api_key=st.session_state.get("openai_api_key"))

        patent_list_text = ""
        for _, row in selected_patents.iterrows():
            patent_list_text += f"- **{row['publication_number']} ({row.get('assignee', 'N/A')})**\n"
            patent_list_text += f"  - **タイトル:** {row['title']}\n"
            patent_list_text += f"  - **要約:** {row['abstract']}\n\n"

        prompt = GENERATE_REPORT_PROMPT.format(plan=plan, patent_list_text=patent_list_text)
        
        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"レポート生成中にエラーが発生しました: {e}"