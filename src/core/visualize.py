import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def plot_publication_trend(df: pd.DataFrame) -> go.Figure:
    """
    検索結果のDataFrameから出願年次推移の棒グラフを生成する。
    """
    if df.empty or 'publication_date' not in df.columns:
        return go.Figure().update_layout(title="データがありません")

    # 日付をdatetime型に変換し、年を抽出
    df['year'] = pd.to_datetime(df['publication_date'], format='%Y%m%d').dt.year
    
    # 年ごとの件数を集計
    trend_data = df['year'].value_counts().sort_index()
    
    fig = px.bar(
        trend_data,
        x=trend_data.index,
        y=trend_data.values,
        labels={'x': '公開年', 'y': '出願件数'},
        title='出願年次推移'
    )
    fig.update_layout(
        xaxis_title="公開年",
        yaxis_title="出願件数",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig

def plot_assignee_ranking(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """
    検索結果のDataFrameから出願人ランキングの横棒グラフを生成する。
    """
    if df.empty or 'assignee' not in df.columns:
        return go.Figure().update_layout(title="データがありません")

    # 出願人を集計（NaNを除外）
    assignee_counts = df['assignee'].dropna().value_counts().nlargest(top_n)
    
    fig = px.bar(
        assignee_counts,
        x=assignee_counts.values,
        y=assignee_counts.index,
        orientation='h',
        labels={'x': '出願件数', 'y': '出願人'},
        title=f'出願人ランキング TOP {top_n}'
    )
    fig.update_layout(
        xaxis_title="出願件数",
        yaxis_title="出願人",
        yaxis={'categoryorder':'total ascending'}, # 件数が多い順に上から表示
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig
