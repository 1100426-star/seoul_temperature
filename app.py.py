import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="서울 연도별 기온 분석", layout="wide")
st.title("서울 연도별 평균기온 분석")

# ── 데이터 로드 ──────────────────────────────────────────────────
@st.cache_data
def load_data(path="seoul_temperature.csv"):
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        dtype={"지점": str},
    )
    df["날짜"] = df["날짜"].str.strip().str.replace("\t", "", regex=False)
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month
    for col in ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["일교차(℃)"] = df["최고기온(℃)"] - df["최저기온(℃)"]
    return df.dropna(subset=["날짜", "연도"])

df = load_data()

# ── 사이드바: 연도 범위 슬라이더 ──────────────────────────────────
min_year = int(df["연도"].min())
max_year = int(df["연도"].max())

with st.sidebar:
    st.header("설정")
    year_range = st.slider(
        "연도 범위",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1,
    )
    window = st.slider("이동평균 구간 (년)", min_value=3, max_value=10, value=5, step=1)

y_start, y_end = year_range
filtered = df[(df["연도"] >= y_start) & (df["연도"] <= y_end)].copy()

# ── 탭 구성 ──────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["연도별 추이", "월별 히트맵", "극값 & 일교차"])

# ─────────────────────────────────────────────────────────────────
# 탭 1: 연도별 추이
# ─────────────────────────────────────────────────────────────────
with tab1:
    yearly = (
        filtered.groupby("연도")
        .agg(
            평균기온=("평균기온(℃)", "mean"),
            최저기온=("최저기온(℃)", "mean"),
            최고기온=("최고기온(℃)", "mean"),
        )
        .round(2)
        .reset_index()
    )

    yearly["이동평균"] = yearly["평균기온"].rolling(window=window, min_periods=1).mean().round(2)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=yearly["연도"],
            y=yearly["평균기온"],
            mode="lines+markers",
            name="연도별 평균기온",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=5),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=yearly["연도"],
            y=yearly["이동평균"],
            mode="lines",
            name=f"{window}년 이동평균",
            line=dict(color="#d62728", width=3, dash="dash"),
        )
    )

    fig.update_layout(
        title=f"서울 연도별 평균기온 ({y_start:,}년–{y_end:,}년)",
        xaxis_title="연도",
        yaxis_title="평균기온 (℃)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        margin=dict(l=40, r=20, t=50, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

    if not yearly.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("평균 기온 (선택 구간)", f"{yearly['평균기온'].mean():.2f} ℃")
        with col2:
            st.metric("최고 기온 (선택 구간)", f"{yearly['최고기온'].max():.2f} ℃")
        with col3:
            st.metric("최저 기온 (선택 구간)", f"{yearly['최저기온'].min():.2f} ℃")

        with st.expander("원본 연도별 데이터 표"):
            st.dataframe(yearly, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────
# 탭 2: 월별 히트맵
# ─────────────────────────────────────────────────────────────────
with tab2:
    heatmap_data = (
        filtered.groupby(["연도", "월"])["평균기온(℃)"]
        .mean()
        .round(2)
        .unstack(fill_value=None)
    )

    years = sorted(heatmap_data.index.tolist())
    months = list(range(1, 13))
    z = heatmap_data.values.tolist()

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=z,
            x=months,
            y=years,
            colorbar=dict(title="평균기온 (℃)"),
            colorscale="RdYlBu_r",
            hovertemplate="연도: %{y}<br>월: %{x}<br>평균기온: %{z:.2f} ℃<extra></extra>",
        )
    )

    fig_heat.update_layout(
        title=f"월별 평균기온 히트맵 ({y_start:,}년–{y_end:,}년)",
        xaxis_title="월",
        yaxis_title="연도",
        xaxis=dict(tickmode="array", tickvals=months, ticktext=[f"{m}월" for m in months]),
        margin=dict(l=60, r=40, t=50, b=60),
        template="plotly_white",
    )

    st.plotly_chart(fig_heat, use_container_width=True)

# ─────────────────────────────────────────────────────────────────
# 탭 3: 극값 & 일교차
# ─────────────────────────────────────────────────────────────────
with tab3:
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("최고기온 상위 10일")
        top10_high = (
            filtered.nlargest(10, "최고기온(℃)")
            .loc[:, ["날짜", "연도", "월", "최고기온(℃)"]]
            .copy()
        )
        top10_high["날짜"] = top10_high["날짜"].dt.strftime("%Y-%m-%d")
        top10_high = top10_high.sort_values("최고기온(℃)", ascending=False).reset_index(drop=True)
        top10_high.insert(0, "순위", range(1, len(top10_high) + 1))
        st.dataframe(top10_high, use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("최저기온 하위 10일")
        top10_low = (
            filtered.nsmallest(10, "최저기온(℃)")
            .loc[:, ["날짜", "연도", "월", "최저기온(℃)"]]
            .copy()
        )
        top10_low["날짜"] = top10_low["날짜"].dt.strftime("%Y-%m-%d")
        top10_low = top10_low.sort_values("최저기온(℃)", ascending=True).reset_index(drop=True)
        top10_low.insert(0, "순위", range(1, len(top10_low) + 1))
        st.dataframe(top10_low, use_container_width=True, hide_index=True)

    # ── 연도별 평균 일교차 그래프 ────────────────────────────────
    st.divider()
    st.subheader("연도별 평균 일교차 (최고기온 − 최저기온)")

    yearly_range = (
        filtered.groupby("연도")["일교차(℃)"]
        .mean()
        .round(2)
        .reset_index()
    )
    yearly_range["이동평균"] = yearly_range["일교차(℃)"].rolling(window=window, min_periods=1).mean().round(2)

    fig_range = go.Figure()

    fig_range.add_trace(
        go.Scatter(
            x=yearly_range["연도"],
            y=yearly_range["일교차(℃)"],
            mode="lines+markers",
            name="연도별 평균 일교차",
            line=dict(color="#2ca02c", width=2),
            marker=dict(size=5),
        )
    )

    fig_range.add_trace(
        go.Scatter(
            x=yearly_range["연도"],
            y=yearly_range["이동평균"],
            mode="lines",
            name=f"{window}년 이동평균",
            line=dict(color="#9467bd", width=3, dash="dash"),
        )
    )

    fig_range.update_layout(
        title=f"서울 연도별 평균 일교차 ({y_start:,}년–{y_end:,}년)",
        xaxis_title="연도",
        yaxis_title="일교차 (℃)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        margin=dict(l=40, r=20, t=50, b=40),
    )

    st.plotly_chart(fig_range, use_container_width=True)
