# Deep reinforcement learning for joint functional split and network function placement in vRAN

## Description
This repository aims to demonstrate the DRL solution implementation. We tested in Ubuntu 20.04 LTS, with Python version 3.6.15 and TensorFlow
version 1.15.4, using Stable Baselines 2.

- [Topologies](#topologies)
- [Paths](#paths)
- [Final Results](#final-results)
- [Comparing Solutions](#comparing-solutions)
- [Citation](#citation)

## Topologies

To evaluate our solution and compare our results with other works, we used a set of topologies with different sizes, from 8 nodes to 512 nodes. The topologies are hierarchical topologies where the CRs are positioned following a layer order. Each CR has an RU, except the red CR highlighted in the figure.

The CRs are free to allocate different amounts of Virtualized Network Functions (VNF).  In other words, they are free to act as a Core Unite (CU) or/and a Distributed Unit (DU). Also, the numbers of CUs or DUs are dynamic, i. e., there is no fixed number of CUs or DUs in our model.

<p float="left">
  <img src="https://github.com/LABORA-INF-UFG/paper-GVAK-2022/blob/main/Figures/Topologies.png" width="800" \>
</p>

## Paths

To calculate the routing paths to be used by our solution, we used the k-shortest path algorithm. Each path can be used with different configurations of allocation points, given that the paths reaches a set of CRs. In this case, we consider all the configurations available.

## Final Results

To see our final results, i. e., the comparison of the centralization level between the solutions, the VNCs used and the learning curve of the DRL agent in the training, we provide a set of charts that illustrate such results for each topology used. The scripts and solutions used to plot those charts are available in this repository.

We compare our DRL agent with two optimal solutions:
  - [*PlaceRAN*](https://github.com/LABORA-INF-UFG/paper-FGLKLRC-2021) - optimization model
  - [*Constrained Deep Reinforcement Based Functional Split Optimization in Virtualized RANs*](https://arxiv.org/abs/2106.00011) - optimization model

## Comparing Solutions

- VNC choices

<p float="left">
  <img src="https://github.com/LABORA-INF-UFG/paper-GVAK-2022/blob/main/Figures/Fig1.png" width="800" \>
</p>

- Centralization level and Learning curve

<p float="left">
  <img src="https://github.com/LABORA-INF-UFG/paper-GVAK-2022/blob/main/Figures/Fig2.png" width="400" />
  <img src="https://github.com/LABORA-INF-UFG/paper-GVAK-2022/blob/main/Figures/Fig3.png" width="400" />
</p>

## Citation

Will be available soon.
