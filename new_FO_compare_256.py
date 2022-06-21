import plotly.graph_objects as go
import json

scenarios = ['Scenario-1', 'Scenario-2', 'Scenario-3', 'Scenario-4', 'Scenario-5', 'Scenario-6', 'Scenario-7']

fig = go.Figure()

y_optimal = []
y_det = []
y_nondet = []

for i in range(1, 8):
    file = open("results/256_CRs/800k_timesteps/C{}.json".format(i))
    json_file = json.load(file)
    y_det.append(json_file["FO1"]*-1)
    y_nondet.append(json_file["FO2"]*-1)

y_optimal = [231, 214, 232, 228, 234, 248, 211]
# y_det=[19, 21, 21, 21, 21, 21, 19]
# y_nondet = [19, 21, 21, 20, 21, 21, 19]
#
y_det_txt = []
for i in range(0, len(y_det)):
    y_det_txt.append(round(1 - y_det[i]/y_optimal[i], 2))

y_nondet_txt = []
for i in range(0, len(y_det)):
    y_nondet_txt.append(round(1 - y_nondet[i]/y_optimal[i], 2))

fig.add_trace(go.Bar(
    x=scenarios,
    y=y_optimal,
    name='Optimal Solution',
    marker_color='blue'
))

fig.add_trace(go.Bar(
    x=scenarios,
    y=y_det,
    name='DRL-Deterministic',
    marker_color='indianred',
    text=y_det_txt
))
fig.add_trace(go.Bar(
    x=scenarios,
    y=y_nondet,
    name='DRL-Nondeterministic',
    marker_color='lightsalmon',
    text=y_nondet_txt
))

fig.update_yaxes(showgrid=True)

# Here we modify the tickangle of the xaxis, resulting in rotated labels.
fig.update_layout(barmode='group', xaxis_tickangle=-45, title={
        'text': "Comparing solutions",
        'y':1,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'})
fig.show()