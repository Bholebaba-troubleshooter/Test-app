import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Will my money last?", page_icon="💰", layout="wide")

st.title("💰 Will my money last?")
st.write(
    "Markets go up and down, so nobody knows the future. This tool runs **2,000 possible "
    "futures** with random market returns and shows how often your savings survive. "
    "Move the sliders on the left to see what changes."
)

# ---------- Inputs (sidebar) ----------
with st.sidebar:
    st.header("About you")
    age = st.slider("Your age today", 20, 70, 35)
    retire_age = st.slider("Retirement age", age + 1, 80, max(age + 1, 60))
    end_age = st.slider("Plan until age", retire_age + 1, 105, 90)

    st.header("Money")
    savings = st.number_input("Savings today", 0, 50_000_000, 200_000, step=10_000)
    contribution = st.number_input("Saved per year until retirement", 0, 2_000_000, 20_000, step=1_000)
    spending = st.number_input("Spent per year in retirement (today's money)", 0, 2_000_000, 40_000, step=1_000)

    st.header("Markets")
    exp_return = st.slider("Expected yearly return (%)", 0.0, 12.0, 7.0, 0.5) / 100
    volatility = st.slider("Ups and downs (volatility, %)", 0.0, 30.0, 15.0, 1.0) / 100
    inflation = st.slider("Inflation (%)", 0.0, 10.0, 3.0, 0.5) / 100

    st.caption("Everything is shown in **today's money**, so inflation is already taken out.")

N_SIMS = 2000


@st.cache_data
def simulate(age, retire_age, end_age, savings, contribution, spending,
             exp_return, volatility, inflation):
    rng = np.random.default_rng(42)  # fixed seed so the chart doesn't jitter
    years = end_age - age
    real_mean = (1 + exp_return) / (1 + inflation) - 1
    returns = np.clip(rng.normal(real_mean, volatility, (N_SIMS, years)), -0.95, None)

    balance = np.zeros((N_SIMS, years + 1))
    balance[:, 0] = savings
    for t in range(years):
        current_age = age + t
        grown = balance[:, t] * (1 + returns[:, t])
        if current_age < retire_age:
            grown += contribution
        else:
            grown -= spending
        balance[:, t + 1] = np.maximum(grown, 0)  # can't go below zero
    return balance


balance = simulate(age, retire_age, end_age, savings, contribution, spending,
                   exp_return, volatility, inflation)
ages = np.arange(age, end_age + 1)

# ---------- Results ----------
success = (balance[:, -1] > 0).mean() * 100
median_end = np.median(balance[:, -1])
at_retire = np.median(balance[:, retire_age - age])

if success >= 85:
    st.success(f"✅ In **{success:.0f}%** of futures your money lasts to age {end_age}. That looks solid.")
elif success >= 60:
    st.warning(f"⚠️ In **{success:.0f}%** of futures your money lasts to age {end_age}. It's a gamble.")
else:
    st.error(f"🚨 Only **{success:.0f}%** of futures last to age {end_age}. Consider saving more or spending less.")

c1, c2, c3 = st.columns(3)
c1.metric("Chance money lasts", f"{success:.0f}%")
c2.metric(f"Typical pot at {retire_age}", f"{at_retire:,.0f}")
c3.metric(f"Typical pot at {end_age}", f"{median_end:,.0f}")

# ---------- Fan chart ----------
p10, p25, p50, p75, p90 = np.percentile(balance, [10, 25, 50, 75, 90], axis=0)
fig = go.Figure()
for lo, hi, name, color in [
    (p10, p90, "80% of futures", "rgba(31,119,180,0.15)"),
    (p25, p75, "Middle 50% of futures", "rgba(31,119,180,0.30)"),
]:
    fig.add_trace(go.Scatter(x=ages, y=hi, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ages, y=lo, fill="tonexty", fillcolor=color,
                             line=dict(width=0), name=name, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=ages, y=p50, name="Typical (median) future",
                         line=dict(color="rgb(31,119,180)", width=3)))
fig.add_vline(x=retire_age, line_dash="dash", annotation_text="Retirement")
fig.update_layout(title="How your savings could evolve (today's money)",
                  xaxis_title="Age", yaxis_title="Savings", height=480,
                  legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig, use_container_width=True)

# ---------- When does money run out? ----------
ran_out = balance[:, -1] == 0
if ran_out.any():
    depleted_age = ages[np.argmax(balance[ran_out] == 0, axis=1)]
    hist = go.Figure(go.Histogram(x=depleted_age, marker_color="indianred"))
    hist.update_layout(title="In the futures where money ran out, at what age?",
                       xaxis_title="Age money ran out", yaxis_title="Number of futures", height=300)
    st.plotly_chart(hist, use_container_width=True)

with st.expander("How does this work?"):
    st.write(
        "Each of the 2,000 futures draws a random return for every year, centred on your "
        "expected return but bouncing around by the volatility you chose. This is called a "
        "**Monte Carlo simulation**. It's an illustration, not financial advice."
    )
