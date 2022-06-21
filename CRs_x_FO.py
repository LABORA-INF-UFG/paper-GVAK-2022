import plotly.express as px
import pandas as pd
import json

k_set = [8, 16, 32, 64, 126, 256, 500]

# murti
y1 = [22, 46, 88, 136, 286, 133, -69]
agg_murti = [y1[i] + k_set[i] for i in range(0, len(k_set))]

# DRL
y4 = [15, 39, 75, 159, 299, 217, 321]
agg_drl = [y4[i] + k_set[i] for i in range(0, len(k_set))]

# PlaceRAN
y3 = [22, 46, 95, 165, 399, 436, 796]
agg_placeran = [y3[i] + k_set[i] for i in range(0, len(k_set))]

df = pd.DataFrame(dict(
    scenarios=k_set,
    Murti_optimal=agg_murti,
    PlaceRAN_optimal=agg_placeran,
    DRL_PlaceRAN=agg_drl
))

print(df)

fig = px.histogram(df, x=["8", "16", "32", "64", "126", "256", "500"],
                   y=["Murti_optimal", "DRL_PlaceRAN", "PlaceRAN_optimal"], barmode='group', height=400)

fig.update_layout(
    title="",
    xaxis_title="Number of CRs (#)",
    yaxis_title="Centralization level (#)",
    legend_title="",
    font=dict(
        family="Arial",
        size=20,
        color="black"
    ),
    yaxis = dict(
        tickfont=dict(size=25)),
    xaxis=dict(
        tickfont=dict(size=25)),
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    ),
    plot_bgcolor='rgba(0,0,0,0)'
)


fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

fig.update_xaxes(showline=True, linewidth=1, linecolor='black', mirror=True)
fig.update_yaxes(showline=True, linewidth=1, linecolor='black', mirror=True)

series_names = ["[12]", "DRL Agent", "PlaceRAN"]

for idx, name in enumerate(series_names):
    fig.data[idx].name = name
    fig.data[idx].hovertemplate = name

fig.show()
