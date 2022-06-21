import plotly.express as px
import pandas as pd

df = pd.DataFrame(dict(
    model=["\u2756", "\u2628", "\u2982", "", "\u2756 ", "\u2628 ", "\u2982 ", " ",
           "\u2756  ", "\u2628  ", "\u2982  ", "  ", "\u2756   ", "\u2628   ", "\u2982    ", "   ",
           "\u2756    ", "\u2628    ", "\u2982     ", "    ", "\u2756     ", "\u2628     ", "\u2982      ", "     ",
           "\u2756       ", "\u2628      ", "\u2982       "],
    C_RAN=[5/5 * 100, 0, 5/5 * 100, 0,
           7/10 * 100, 0, 7/10 * 100, 0,
           14/19 * 100, 0, 14/19 * 100, 0,
           13/35 * 100, 0, 0, 0,
           7/80 * 100, 0, 41/80 * 100, 0,
           0, 0, 45/122 * 100, 0,
           0, 27/213 * 100, 116/213 * 100],
    NG_RAN_3=[0, 5/5 * 100, 0, 0,
              0, 10/10 * 100, 3/10 * 100, 0,
              0, 19/19 * 100, 4/19 * 100, 0,
              0, 35/35 * 100, 35/35 * 100, 0,
              0, 65/80 * 100, (10+29)/80 * 100, 0,
              0, 65/122 * 100, (40+1)/122 * 100, 0,
              0, 65/213 * 100, 47/213 * 100],
    NG_RAN_2=[0, 0, 0, 0,
              3/10 * 100, 0, 0, 0,
              5/19 * 100, 0, 1/19 * 100, 0,
              22/35 * 100, 0, 0, 0,
              (27+20)/80 * 100, 15/80 * 100, 0, 0,
              (46+19)/122 * 100, 57/122 * 100, 36/122 * 100, 0,
              (44+21)/213 * 100, 121/213 * 100, 50/213 * 100],
    D_RAN=[0, 0, 0, 0,
           0, 0, 0, 0,
           0, 0, 0, 0,
           0, 0, 0, 0,
           26/80 * 100, 0, 0, 0,
           57/122 * 100, 0, 0, 0,
           148/213 * 100, 0, 0]
))

print(df)

fig = px.bar(df, x="model", y=["C_RAN", "NG_RAN_3", "NG_RAN_2", "D_RAN"],
             color_discrete_map={"C_RAN": "#E9B914", "NG_RAN_3": "#123BD3", "NG_RAN_2": "#BCBCBC", "D_RAN": "#CD190A"}, height=300)

series_names = ["C-RAN", "NG-RAN(3)", "NG-RAN(2)", "D-RAN"]

for idx, name in enumerate(series_names):
    fig.data[idx].name = name
    fig.data[idx].hovertemplate = name

fig.update_layout(
    title="",
    xaxis_title="CRs (#)",
    yaxis_title="VNCs (%)",
    legend_title="",
    font=dict(
        family="Arial",
        size=20,
        color="black"
    ),
    yaxis=dict(
        tickfont=dict(size=25), range=[0, 130]),
    xaxis=dict(
        tickfont=dict(size=25)),
    # legend=dict(
    #     yanchor="top",
    #     y=2.0,
    #     xanchor="left",
    #     x=0.01
    # ),
    plot_bgcolor='rgba(0,0,0,0)',
)

fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

fig.update_xaxes(showline=True, linewidth=1, linecolor='black', mirror=True)
fig.update_yaxes(showline=True, linewidth=1, linecolor='black', mirror=True)

fig.show()