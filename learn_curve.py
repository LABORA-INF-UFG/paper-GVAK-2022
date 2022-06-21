import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import json

max_len = 5000

topo_8_file = open("learn_curve_8.json", "r")
topo_8_obj = json.load(topo_8_file)

topo_16_file = open("learn_curve_16.json", "r")
topo_16_obj = json.load(topo_16_file)

topo_32_file = open("learn_curve_32.json", "r")
topo_32_obj = json.load(topo_32_file)

topo_64_file = open("learn_curve_64.json", "r")
topo_64_obj = json.load(topo_64_file)

topo_128_file = open("learn_curve_128.json", "r")
topo_128_obj = json.load(topo_128_file)

topo_256_file = open("learn_curve_256.json", "r")
topo_256_obj = json.load(topo_256_file)

topo_512_file = open("learn_curve_512.json", "r")
topo_512_obj = json.load(topo_512_file)

topo_8_data = [i + 5 for i in topo_8_obj["values"][:max_len]]

topo_16_data = [i + 10 for i in topo_16_obj["values"][:max_len]]

topo_32_data = [i + 19 for i in topo_32_obj["values"][:max_len]]

topo_64_data = [i + 35 for i in topo_64_obj["values"][:max_len]]

topo_128_data = [i + 80 for i in topo_128_obj["values"][:max_len]]

topo_256_data = [i + 122 for i in topo_256_obj["values"][:max_len]]

topo_512_data = [i + 213 for i in topo_512_obj["values"][:max_len]]

print(len(topo_64_obj["values"]))

# Create some mock data
x_epsilon = np.arange(0, max_len, 1)

# #FO values Optimal and Heuristic resp...
# optimal_search = [49, 37, 37, 37, 37, 37, 37, 37, 37, 37, 34, 25, 22, 22,
#                     18, 15, 12, 5, 3, 1, 0, 0, 0, -1, -1, -1, -1, -1,
#                     -1, -11, -11, -11, -11, -15, -37, -40, -82, -97,
#                     -102, -110, -120, -130, -149, -154, -161, -164, -165, -166,
#                     -167, -167, -167, -167, -167, -178, -189, -194, -201, -201, -202]
# heuristic_search = [49, 37, 36, 30, 16, 11, 6, 5, 3, -8, -10, -12, -17, -19,
#                   -20, -20, -26, -31, -37, -44, -49, -51, -65, -67, -74, -75, -89, -95,
#                   -100, -101, -102, -110, -111, -115, -119, -127, -143, -154,
#                   -158, -162, -166, -170, -175, -175, -175, -178, -187, -193,
#                   -195, -197, -198, -202, -203, -204, -204, -204, -205, -206, -206]

fig, ax1 = plt.subplots(figsize=(11, 5))
# labels = [item.get_text() for item in ax1.get_xticklabels()]
# for i in range(1, 36):
#     labels.append(str(i))
# ax1.set_xticklabels(labels)

ax1.plot(x_epsilon, topo_8_data, color='dimgray', linewidth=3)
ax1.plot(x_epsilon, topo_16_data, color='maroon', linewidth=3)
ax1.plot(x_epsilon, topo_32_data, color='royalblue', linewidth=3)
ax1.plot(x_epsilon, topo_64_data, color='navy', linewidth=3)
#plt.yscale("log")
#plt.yticks([10**4, 10**5, 10**6, 10**7, 10**8, 10**9])

# tamanho fontes em X e Y
ax1.tick_params(axis='x', which='major', labelsize=28)
ax1.tick_params(axis='y', which='major', labelsize=28)
#
# #labels text and size
ax1.set_ylabel('Reward (#)', fontsize=28)
ax1.set_xlabel('Episode', fontsize=28)

#set X grid
ax1.yaxis.grid(color='gray', linestyle='dashed', linewidth=0.5)
ax1.xaxis.grid(color='gray', linestyle='dashed', linewidth=0.5)
fig.tight_layout()

plt.rcParams.update({'font.size': 24})

# legend_elements = [Line2D([0], [0], color='black', lw=3, label='8 CRs'),
#                    Line2D([0], [0], color='gray', lw=3, label='16 CRs'),
#                    Line2D([0], [0], color='steelblue', lw=3, label='32 CRs'),
#                    Line2D([0], [0], color='royalblue', lw=3, label='64 CRs')]
# plt.legend(handles=legend_elements, loc="lower right")

plt.xlim(0.5, 5000)
plt.savefig("Figure_3.pdf", bbox_inches='tight')
plt.show()