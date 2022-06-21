import itertools

import gym
import json
from gym import error, spaces, utils
import numpy as np
import random
from model.model import Path, CR, DRC, FS, RU
import math

# Global vars
links = []
capacity = {}  # link capacity in Gbps
delay = {}  # link delay in ms
crs = {}  # CR CPU capacity # of cores
paths = {}
conj_Fs = {}
learn_points = []

C1 = {}
for i in range(3, 257):
    if i in range(3, 22):
        C1[str(i)] = 1
    else:
        C1[str(i)] = 0.5

C2 = {}
for i in range(3, 257):
    if i in range(3, 22):
        C2[str(i)] = 0.5
    else:
        C2[str(i)] = 1

C3 = {}
for i in range(3, 257):
    C3[str(i)] = 0.5

C4 = {}
for i in range(3, 257):
    if i in range(3, 22):
        C4[str(i)] = random.randint(1, 5) / 10
    else:
        C4[str(i)] = random.randint(5, 10)/10

C5 = {}
for i in range(3, 257):
    if i in range(3, 22):
        C5[str(i)] = random.randint(5, 10)/10
    else:
        C5[str(i)] = random.randint(1, 5)/10

C6 = {}
for i in range(3, 257):
    C6[str(i)] = 0.1

C7 = {}
for i in range(3, 257):
    C7[str(i)] = 1

C = C7
Cs = "C7"


class MppRanEnv(gym.Env):

    def __init__(self, **kwargs):

        self.best_FO = 0
        # ENCONTRANDO TOPOLOGIA
        self.count_certralization = 0
        self.end_ep = False
        if len(kwargs) > 0 and kwargs['topology']:
            self.topology = kwargs['topology']
        if len(kwargs) > 0 and kwargs['nactions']:
            self.n_actions = kwargs['nactions']
        if len(kwargs) > 0 and kwargs['demand_per_RU']:
            self.rus_demand_entry = kwargs['demand_per_RU']
            if kwargs['demand_per_RU'] == "C7":
                self.rus_demand_entry = C7

        # LEITURA DOS ARQUIVOS DA TOPOLOGIA (NODES, LINKS, PATHS) MESMOS ARQUIVOS DO SOLVER
        self.nodes_file = "/home/gmfaria6/workspace/DRL/DRL-MPP-RAN/topology/murti_files/murti_{topology}_CRs_nodes.json".format(topology=self.topology)
        self.links_file = "/home/gmfaria6/workspace/DRL/DRL-MPP-RAN/topology/murti_files/murti_{topology}_CRs_links.json".format(topology=self.topology)
        self.paths_file = "/home/gmfaria6/workspace/DRL/DRL-MPP-RAN/topology/murti_files/{topology}_CRs_paths.json".format(topology=self.topology)

        self.reward = 0
        self.continuous_observation_space = []

        # LENDO A TOPOLOGIA COM MESMO MÉTODO DO SOLVER - CRIANDO NODES, LINKS E PATHS
        self.read_topology()

        # a = LISTA QUE CONTÉM A QUANTIDADE DE CRS EM CADA CAMINHO
        paths_seq_len = [np.count_nonzero(paths[p].seq) for p in paths]

        # delay_paths = LISTA QUE CONTÉM OS DELAYS [P1, P2, P3] DE CADA PATH
        delays_paths = [[paths[dp].delay_p1, paths[dp].delay_p2, paths[dp].delay_p3] for dp in paths]

        # CRIANDO DRCs DE ACORDO COM QUANTIDADE DE CRs E DELAY DOS LINKS (CRIAÇÃO OTIMIZADA DE APENAS DRCS POSSÍVEIS)
        self.DRCs = self.DRC_structure(drc_max_len=np.max(paths_seq_len), delays_paths=delays_paths)

        # CRIANDO RUs MESMO MÉTODO DO SOLVER
        self.rus = self.RU_location()

        # d_rus = DICT COM {CR: QTD_RUS}
        self.d_rus = {key: crs.get(key).rus for key in crs if crs.get(key).rus > 0}

        self.links_capacity = []
        self.links_index = {}
        self.crs_fs = {}

        for cr in crs:
            self.crs_fs[cr] = {'f8': 0, 'f7': 0, 'f6': 0, 'f5': 0, 'f4': 0, 'f3': 0, 'f2': 0, 'f1': 0, 'f0': 0}

        count = 0
        for l in capacity:
            self.links_index[l] = count
            count += 1
            self.links_capacity.append(capacity[l])

        if len(kwargs) > 0 and kwargs['nactions']:
            self.n_actions = kwargs['nactions']

        self.RUs_list = []
        for cr in self.d_rus:
            self.RUs_list.append(cr)

        self.RUs_list.sort()
        candidate = self.RUs_list.pop(0)

        # DICT COM CRS E SE EXISTE OU NAO RU NELE {'cr_id': RU_demand}
        # self.rus_demand_entry = {'3': 1, '4': 1, '5': 1, '6': 1, '7': 0.3, '8': 0.3, '9': 0.3, '10': 0.3}

        # CRIANDO ESPAÇO DE OBSERVAÇÃO
        self.links_capacity = []
        self.links_index = {}
        count = 0
        for l in capacity:
            self.links_index[l] = count
            count += 1
            self.links_capacity.append(capacity[l])

        self.observation_space = [100 for l in self.links_capacity]

        count_crs = len(self.observation_space)
        self.crs_index = {}

        for cr in crs:
            self.observation_space.append(100)
            self.crs_index[cr] = count_crs
            count_crs += 1

        self.observation_space.append(self.n_actions[0])

        self.continuous_observation_space = self.observation_space

        self.actions = self.validate_acts([(p, d) for p in paths if paths[p].seq[2] == candidate for d in self.DRCs])

        self.action_space = spaces.Discrete(len(self.actions))

        self.demand_count = 0

        self.observation_space = np.array(self.observation_space)

        self.observation_space = spaces.Box(low=-5000, high=5000,
                                            shape=(len(self.observation_space),), dtype=np.float64)

        cr_min = np.inf
        for cr in self.d_rus:
            if cr < cr_min:
                cr_min = cr

        self.minor_CR_index = cr_min

    def reset(self):  # Required by script to initialize the observation space
        self.read_topology()
        self.end_ep = False
        self.reward = 0
        self.count_certralization = 0
        self.demand_count = 0

        self.crs_fs = {}

        for cr in crs:
            self.crs_fs[cr] = {'f8': 0, 'f7': 0, 'f6': 0, 'f5': 0, 'f4': 0, 'f3': 0, 'f2': 0, 'f1': 0, 'f0': 0}

        self.RUs_list = []
        for cr in self.d_rus:
            self.RUs_list.append(cr)

        self.RUs_list.sort()

        # validate actions permite apenas ações que fazem sentido (capacidade link, qtd de CRs, etc)

        candidate = self.RUs_list.pop(0)

        # CRIANDO ESPAÇO DE OBSERVAÇÃO
        self.links_capacity = []
        self.links_index = {}
        count = 0
        for l in capacity:
            self.links_index[l] = count
            count += 1
            self.links_capacity.append(capacity[l])

        self.observation_space = [100 for l in self.links_capacity]

        count_crs = len(self.observation_space)
        self.crs_index = {}

        for cr in crs:
            self.observation_space.append(100)
            self.crs_index[cr] = count_crs
            count_crs += 1

        self.observation_space.append(self.n_actions[0])

        self.continuous_observation_space = self.observation_space

        self.actions = self.validate_acts([(p, d) for p in paths if paths[p].seq[2] == candidate for d in self.DRCs])

        self.action_space = spaces.Discrete(len(self.actions))

        self.observation_space = np.array(self.observation_space)

        return self.observation_space

    def step(self, action_index):
        # if self.demand_count > 3:
        #     self.demand_count = 0
        # if self.demand_count == 0:
        #     self.rus_demand_entry = C7
        # elif self.demand_count == 1:
        #     self.rus_demand_entry = C5
        # elif self.demand_count == 2:
        #     self.rus_demand_entry = C4
        # elif self.demand_count == 3:
        #     self.rus_demand_entry = C3
        if action_index >= len(self.actions):
            self.reward = -1 * (len(self.RUs_list) + 1)
            self.end_ep = True
            info = {"is_success": False}
        else:
            action = self.actions[action_index]
            action_path = paths[action[0]]
            action_DRC = self.DRCs[action[1]]
            penalty = False

            # LINKS CAPACITY UPDATE
            for l in action_path.p1:
                cons = (action_DRC.bw_BH / self.links_capacity[self.links_index[l]]) * 100
                self.continuous_observation_space[self.links_index[l]] -= cons
                self.observation_space[self.links_index[l]] = int(self.continuous_observation_space[self.links_index[l]])+1

            for l in action_path.p2:
                cons = (action_DRC.bw_MH / self.links_capacity[self.links_index[l]]) * 100
                self.continuous_observation_space[self.links_index[l]] -= cons
                self.observation_space[self.links_index[l]] = int(self.continuous_observation_space[self.links_index[l]])+1

            for l in action_path.p3:
                cons = (action_DRC.bw_FH / self.links_capacity[self.links_index[l]]) * 100
                self.continuous_observation_space[self.links_index[l]] -= cons
                self.observation_space[self.links_index[l]] = int(self.continuous_observation_space[self.links_index[l]])+1

            # CRS CAPACITY UPDATE
            if action_path.seq[0]:
                cons = (action_DRC.cpu_CU / crs[action_path.seq[0]].cpu) * 100
                self.continuous_observation_space[self.crs_index[action_path.seq[0]]] -= cons
                self.observation_space[self.crs_index[action_path.seq[0]]] = int(self.continuous_observation_space[self.crs_index[action_path.seq[0]]]) + 1

            if action_path.seq[1]:
                cons = (action_DRC.cpu_DU / crs[action_path.seq[1]].cpu) * 100
                self.continuous_observation_space[self.crs_index[action_path.seq[1]]] -= cons
                self.observation_space[self.crs_index[action_path.seq[1]]] = int(
                    self.continuous_observation_space[self.crs_index[action_path.seq[1]]]) + 1

            if action_path.seq[2]:
                cons = (action_DRC.cpu_RU / crs[action_path.seq[2]].cpu) * 100
                self.continuous_observation_space[self.crs_index[action_path.seq[2]]] -= cons
                self.observation_space[self.crs_index[action_path.seq[2]]] = int(
                    self.continuous_observation_space[self.crs_index[action_path.seq[2]]]) + 1

            if not penalty:
                self.observation_space[len(self.observation_space) - 1] -= 1
                for cr in action_path.seq:
                    for f in ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0']:
                        if cr == action_path.seq[0] and f in action_DRC.Fs_CU:
                            self.crs_fs[cr][f] += 1
                        if cr == action_path.seq[1] and f in action_DRC.Fs_DU:
                            self.crs_fs[cr][f] += 1
                        if cr == action_path.seq[2] and f in action_DRC.Fs_RU:
                            self.crs_fs[cr][f] += 1
            else:
                self.reward = -1 * (len(self.RUs_list) + 1)
                self.end_ep = True
                info = {"is_success": False}

            if not self.end_ep:
                if not len(self.RUs_list):
                    info = {"is_success": True}
                    count_crs = 0
                    for cr in self.crs_fs:
                        for f in self.crs_fs[cr]:
                            if self.crs_fs[cr][f]:
                                count_crs += 1
                                break
                    count_agg = 0
                    for cr in self.crs_fs:
                        for f in self.crs_fs[cr]:
                            if self.crs_fs[cr][f]:
                                count_agg += self.crs_fs[cr][f] - 1
                    self.reward = count_agg - count_crs
                    # print("Acertou!!! FO = {}".format(-1 * self.reward))

                    learn_points.append(count_agg)
                    learn_curve = open("learn_curve_512.json", "w")
                    json.dump({"values": learn_points}, learn_curve)

                    self.demand_count += 1
                    self.end_ep = True
                else:
                    candidate = self.RUs_list.pop(0)
                    self.actions = self.validate_acts(
                        [(p, d) for p in paths if paths[p].seq[2] == candidate for d in self.DRCs])
                    self.action_space = spaces.Discrete(len(self.actions))
                    info = {}

        return self.observation_space, self.reward, self.end_ep, info

    def step_validation(self, action_index):
        if action_index >= len(self.actions):
            self.reward = -1 * (len(self.RUs_list) + 1)
            self.end_ep = True
            info = {"is_success": False}
        else:
            print("Path: ", paths[self.actions[action_index][0]])
            print("DRC: ", self.DRCs[self.actions[action_index][1]].id, self.DRCs[self.actions[action_index][1]].Fs_CU,
                  self.DRCs[self.actions[action_index][1]].Fs_DU, self.DRCs[self.actions[action_index][1]].Fs_RU)

            action = self.actions[action_index]
            action_path = paths[action[0]]
            action_DRC = self.DRCs[action[1]]
            penalty = False

            # LINKS CAPACITY UPDATE
            for l in action_path.p1:
                cons = (action_DRC.bw_BH / self.links_capacity[self.links_index[l]]) * 100
                self.continuous_observation_space[self.links_index[l]] -= cons
                self.observation_space[self.links_index[l]] = int(
                    self.continuous_observation_space[self.links_index[l]]) + 1

            for l in action_path.p2:
                cons = (action_DRC.bw_MH / self.links_capacity[self.links_index[l]]) * 100
                self.continuous_observation_space[self.links_index[l]] -= cons
                self.observation_space[self.links_index[l]] = int(
                    self.continuous_observation_space[self.links_index[l]]) + 1

            for l in action_path.p3:
                cons = (action_DRC.bw_FH / self.links_capacity[self.links_index[l]]) * 100
                self.continuous_observation_space[self.links_index[l]] -= cons
                self.observation_space[self.links_index[l]] = int(
                    self.continuous_observation_space[self.links_index[l]]) + 1

            # CRS CAPACITY UPDATE
            if action_path.seq[0]:
                cons = (action_DRC.cpu_CU / crs[action_path.seq[0]].cpu) * 100
                self.continuous_observation_space[self.crs_index[action_path.seq[0]]] -= cons
                self.observation_space[self.crs_index[action_path.seq[0]]] = int(
                    self.continuous_observation_space[self.crs_index[action_path.seq[0]]]) + 1

            if action_path.seq[1]:
                cons = (action_DRC.cpu_DU / crs[action_path.seq[1]].cpu) * 100
                self.continuous_observation_space[self.crs_index[action_path.seq[1]]] -= cons
                self.observation_space[self.crs_index[action_path.seq[1]]] = int(
                    self.continuous_observation_space[self.crs_index[action_path.seq[1]]]) + 1

            if action_path.seq[2]:
                cons = (action_DRC.cpu_RU / crs[action_path.seq[2]].cpu) * 100
                self.continuous_observation_space[self.crs_index[action_path.seq[2]]] -= cons
                self.observation_space[self.crs_index[action_path.seq[2]]] = int(
                    self.continuous_observation_space[self.crs_index[action_path.seq[2]]]) + 1

            if not penalty:
                self.observation_space[len(self.observation_space) - 1] -= 1
                for cr in action_path.seq:
                    for f in ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0']:
                        if cr == action_path.seq[0] and f in action_DRC.Fs_CU:
                            self.crs_fs[cr][f] += 1
                        if cr == action_path.seq[1] and f in action_DRC.Fs_DU:
                            self.crs_fs[cr][f] += 1
                        if cr == action_path.seq[2] and f in action_DRC.Fs_RU:
                            self.crs_fs[cr][f] += 1
            else:
                self.reward = -1 * (len(self.RUs_list) + 1)
                self.end_ep = True
                info = {"is_success": False}

            if not self.end_ep:
                if not len(self.RUs_list):
                    info = {"is_success": True}
                    count_crs = 0
                    for cr in self.crs_fs:
                        for f in self.crs_fs[cr]:
                            if self.crs_fs[cr][f]:
                                count_crs += 1
                                break
                    count_agg = 0
                    for cr in self.crs_fs:
                        for f in self.crs_fs[cr]:
                            if self.crs_fs[cr][f]:
                                count_agg += self.crs_fs[cr][f] - 1
                    self.reward = count_agg - count_crs
                    print("Acertou!!! FO = {}".format(-1 * self.reward))
                    self.demand_count += 1
                    self.end_ep = True
                else:
                    candidate = self.RUs_list.pop(0)
                    self.actions = self.validate_acts(
                        [(p, d) for p in paths if paths[p].seq[2] == candidate for d in self.DRCs])
                    self.action_space = spaces.Discrete(len(self.actions))
                    info = {}

        return self.observation_space, self.reward, self.end_ep, info

    def render(self):
        pass

    def read_topology(self):
        """
      READ T1 TOPOLOGY FILE
      Implements the topology from reading the json file and creates the main structure that is used by the stages of the model.
      :rtype: Inserts topology data into global structures, so the method has no return
      """
        with open(self.links_file) as json_file:
            data = json.load(json_file)

            # Creates the set of links with delay and capacity read by the json file, stores the links in the global list "links"
            json_links = data["links"]
            for item in json_links:
                link = item
                source_node = link["fromNode"]
                destination_node = link["toNode"]

                # Creates links full duplex for each link in the json file
                if source_node < destination_node:
                    capacity[(source_node, destination_node)] = link["capacity"]
                    delay[(source_node, destination_node)] = link["delay"]
                    links.append((source_node, destination_node))
                    # ADD THIS CODE FOR MURTI TOPOLOGY
                    capacity[(destination_node, source_node)] = link["capacity"]
                    delay[(destination_node, source_node)] = link["delay"]
                    links.append((destination_node, source_node))

                # Creates links full duplex for each link in the json file
                else:
                    capacity[(destination_node, source_node)] = link["capacity"]
                    delay[(destination_node, source_node)] = link["delay"]
                    links.append((destination_node, source_node))
                    # ADD THIS CODE FOR MURTI TOPOLOGY
                    capacity[(source_node, destination_node)] = link["capacity"]
                    delay[(source_node, destination_node)] = link["delay"]
                    links.append((source_node, destination_node))

            # Creates the set of CRs with RAM and CPU in a global list "crs" -- cr[0] is the network Core node
            with open(self.nodes_file) as json_file:
                data = json.load(json_file)
                json_nodes = data["nodes"]
                for item in json_nodes:
                    node = item
                    CR_id = node["nodeNumber"]
                    # node_RAM = node["RAM"]
                    node_CPU = node["cpu"]
                    rus = node["RU"]
                    cr = CR(CR_id, node_CPU, 0, rus=rus)
                    crs[CR_id] = cr
            crs[0] = CR(0, 0, 0, 0)

            # Creates the set of previously calculated paths "8_CRs_paths.json". -- the algorithm used to calculate the paths is the k-shortest paths algorithm.
            with open(self.paths_file) as json_paths_file:
                # Reads the file "8_CRs_paths.json" with the paths
                json_paths_f = json.load(json_paths_file)
                json_paths = json_paths_f["paths"]

                # For each path it calculates the id, sets the origin (Core node) and destination (CRs with RUs).
                for item in json_paths:
                    path = json_paths[item]
                    path_id = path["id"]
                    path_source = path["source"]

                    if path_source == "CN":
                        path_source = 0

                    path_target = path["target"]
                    path_seq = path["seq"]

                    # sets the paths p1, p2 and p3 (BH, MH and FH respectively)
                    paths_p = [path["p1"], path["p2"], path["p3"]]

                    list_p1 = []
                    list_p2 = []
                    list_p3 = []

                    for path_p in paths_p:
                        aux = ""
                        sum_delay = 0

                        for tup in path_p:
                            aux += tup
                            tup_aux = tup
                            tup_aux = tup_aux.replace('(', '')
                            tup_aux = tup_aux.replace(')', '')
                            tup_aux = tuple(map(int, tup_aux.split(', ')))
                            if path_p == path["p1"]:
                                list_p1.append(tup_aux)
                            elif path_p == path["p2"]:
                                list_p2.append(tup_aux)
                            elif path_p == path["p3"]:
                                list_p3.append(tup_aux)
                            sum_delay += delay[tup_aux]

                        if path_p == path["p1"]:
                            delay_p1 = sum_delay
                        elif path_p == path["p2"]:
                            delay_p2 = sum_delay
                        elif path_p == path["p3"]:
                            delay_p3 = sum_delay

                        if path_seq[0] == 0:
                            delay_p1 = 0

                        if path_seq[1] == 0:
                            delay_p2 = 0

                    # Creates the paths and store at the global dict "paths"
                    p = Path(path_id, path_source, path_target, path_seq, list_p1, list_p2, list_p3, delay_p1, delay_p2,
                             delay_p3)
                    paths[path_id] = p

    # using murti DRCs
    def DRC_structure(self, drc_max_len=None, delays_paths=None):
        # DRCs MURTI Split 0 = D-RAN
        DRC0 = DRC(0, 0, 1.568, 2.352, 0.01, 0.01, 0.01, [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'],
                   10, 10, 0.01, 9.9, 9.9, 9.9, 2, 0)

        # DRCs MURTI Split 1
        DRC1 = DRC(1, 0.98, 1.568, 2.352, 0.01, 0.01, 0.01, ['f8', 'f7'], ['f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'],
                   10, 10, 0.01, 9.9, 13.2, 42.6, 3, 1)

        # DRCs MURTI Split 2
        DRC2 = DRC(2, 0.98, 1.568, 2.352, 0.01, 0.01, 0.01, ['f8', 'f7', 'f6', 'f5', 'f4', 'f3'], ['f2'], ['f1', 'f0'],
                   10, 0.25, 0.01, 9.9, 13.6, 42.6, 3, 1)

        # DRCs MURTI Split 3
        DRC3 = DRC(3, 0, 2.54, 2.354, 0, 0.01, 0.01, [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'], 10,
                   10, 0.25, 0, 9.9, 42.6, 3, 8)

        DRCs = {0: DRC0, 1: DRC1, 2: DRC2, 3: DRC3}

        if drc_max_len:

            valid_DRCs = {}

            # Creating the sub-set of only topology-valid DRCs
            for d in DRCs:
                if DRCs[d].q_CRs <= drc_max_len:
                    valid_DRCs[DRCs[d].id] = DRCs[d]

            DRCs = valid_DRCs

        if delays_paths:
            valid_DRCs_paths = {}
            for d in DRCs:
                for p in paths:
                    if paths[p].delay_p1 <= DRCs[d].delay_BH and paths[p].delay_p2 <= DRCs[d].delay_MH \
                            and paths[p].delay_p3 <= DRCs[d].delay_FH:
                        if self.paths_delay_comparator(DRCs[d].bw_BH, paths[p].p1) \
                                and self.paths_delay_comparator(DRCs[d].bw_MH, paths[p].p2) \
                                and self.paths_delay_comparator(DRCs[d].bw_FH, paths[p].p3):
                            valid_DRCs_paths[DRCs[d].id] = DRCs[d]
            DRCs = valid_DRCs_paths

        return DRCs

        return DRCs

    # def DRC_structure(self, drc_max_len=None, delays_paths=None):
    #     # IMPLEMENTS T2 Topology DRCs
    #     # Implements the DRCs with cpu usage, VNFs splits and network resources requirements, for T2 Topology
    #     # :rtype: Dict with the DRCs informations
    #
    #     # Creates the DRCs
    #     # (id: DRC): 1 = DRC1, 2 = DRC2, 4 = DRC7 and 5 = DRC8 -- DRCs with 3 independents CRs [CU]-[DU]-[RU]
    #     DRC1 = DRC(1, 0.49, 2.058, 2.352, 0.01, 0.01, 0.01, ['f8'], ['f7', 'f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'],
    #                10, 10, 0.25, 9.9, 13.2, 42.6, 3, 1)
    #     DRC2 = DRC(2, 0.98, 1.568, 2.352, 0.01, 0.01, 0.01, ['f8', 'f7'], ['f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'],
    #                10, 10, 0.25, 9.9, 13.2, 42.6, 3, 2)
    #     DRC4 = DRC(4, 0.49, 1.225, 3.185, 0.01, 0.01, 0.01, ['f8'], ['f7', 'f6', 'f5', 'f4', 'f3'], ['f2', 'f1', 'f0'],
    #                10, 10, 0.25, 9.9, 13.2, 13.6, 3, 7)
    #     DRC5 = DRC(5, 0.98, 0.735, 3.185, 0.01, 0.01, 0.01, ['f8', 'f7'], ['f6', 'f5', 'f4', 'f3'], ['f2', 'f1', 'f0'],
    #                10, 10, 0.25, 9.9, 13.2, 13.6, 3, 8)
    #
    #     # (id: DRC): 6 = DRC12, 7 = DRC13, 9 = DRC18 and 10 = DRC17  -- DRCs with 2 CRs [CU/DU]-[RU] or [CU]-[DU/RU]
    #     DRC6 = DRC(6, 0, 0.49, 4.41, 0, 0.01, 0.01, [0], ['f8'], ['f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'], 0,
    #                10, 10, 0, 9.9, 13.2, 2, 12)
    #     DRC7 = DRC(7, 0, 0.98, 3.92, 0, 0.01, 0.01, [0], ['f8', 'f7'], ['f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'], 0, 10,
    #                10, 0, 9.9, 13.2, 2, 13)
    #     DRC9 = DRC(9, 0, 2.54, 2.354, 0, 0.01, 0.01, [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'], 0,
    #                10, 0.25, 0, 9.9, 42.6, 2, 18)
    #     DRC10 = DRC(10, 0, 1.71, 3.185, 0, 0.01, 0.01, [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3'], ['f2', 'f1', 'f0'], 0,
    #                 10, 0.25, 0, 9.9, 13.6, 2, 17)
    #
    #     # DRCs MAP (id: DRC): 8 = DRC19 -- D-RAN with 1 CR [CU/DU/RU]
    #     DRC8 = DRC(8, 0, 0, 4.9, 0, 0, 0.01, [0], [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'], 0, 0, 10,
    #                0, 0, 9.9, 1, 19)
    #
    #     # Creates the set of DRCs
    #     DRCs = {1: DRC1, 2: DRC2, 4: DRC4, 5: DRC5, 6: DRC6, 7: DRC7, 8: DRC8, 9: DRC9, 10: DRC10}
    #
    #     if drc_max_len:
    #
    #         valid_DRCs = {}
    #
    #         # Creating the sub-set of only topology-valid DRCs
    #         for d in DRCs:
    #             if DRCs[d].q_CRs <= drc_max_len:
    #                 valid_DRCs[DRCs[d].id] = DRCs[d]
    #
    #         DRCs = valid_DRCs
    #
    #     if delays_paths:
    #         valid_DRCs_paths = {}
    #         for d in DRCs:
    #             for p in paths:
    #                 if paths[p].delay_p1 <= DRCs[d].delay_BH and paths[p].delay_p2 <= DRCs[d].delay_MH \
    #                         and paths[p].delay_p3 <= DRCs[d].delay_FH:
    #                     if self.paths_delay_comparator(DRCs[d].bw_BH, paths[p].p1) \
    #                             and self.paths_delay_comparator(DRCs[d].bw_MH, paths[p].p2) \
    #                             and self.paths_delay_comparator(DRCs[d].bw_FH, paths[p].p3):
    #                         valid_DRCs_paths[DRCs[d].id] = DRCs[d]
    #         DRCs = valid_DRCs_paths
    #
    #     return DRCs

    def paths_delay_comparator(self, d_bw, path):
        less = True
        for i, p in enumerate(path):
            if d_bw > capacity[path[i]]:
                less = False
        return less

    def RU_location(self):
        """
    SET THE T2 TOPOLOGY RUs
    Reads the T2 Topology file and define the RUs locations
    :return: Dict with RUs information
    """

        rus = {}
        count = 1
        # Reads the topology file with RUs locations
        with open(self.nodes_file) as json_file:
            data = json.load(json_file)

            json_crs = data["nodes"]

            for item in json_crs:
                node = item
                num_rus = node["RU"]
                num_cr = node["nodeNumber"]

                # Creates the RUs
                for i in range(0, num_rus):
                    rus[count] = RU(count, int(num_cr))
                    count += 1

        return rus

    def validate_acts(self, actions):
        '''
    removing impossible actions
    ex.: path -> [(0,1),(1,7)]
         DRC -> CU = ['f8'], DU = ['f7',...,'f2'], RU = ['f1','f0']
         The path only uses 2 CRs (1 and 7), but the DRC requires 3 CRs
    :param actions: all possible actions
    :return: valid actions - list
    '''
        acts = []
        for ac in actions:
            valid = True
            # is the last cr in path.seq a RU?
            if len([d for d in crs if crs[d].rus > 0 and paths[ac[0]].seq[2] == crs[d].id]) == 0:
                valid = False
            # is there vnfs to be allocated in the path?
            if valid:
                if len(paths[ac[0]].p1) > 0 and isinstance(self.DRCs[ac[1]].Fs_CU[0], int):
                    valid = False
                if len(paths[ac[0]].p2) > 0 and isinstance(self.DRCs[ac[1]].Fs_DU[0], int):
                    valid = False
                if len(paths[ac[0]].p3) > 0 and isinstance(self.DRCs[ac[1]].Fs_RU[0], int):
                    valid = False
            # is there path to accomodate the vnfs?
            if valid:
                if len(paths[ac[0]].p1) == 0 and not isinstance(self.DRCs[ac[1]].Fs_CU[0], int):
                    valid = False
                if len(paths[ac[0]].p2) == 0 and not isinstance(self.DRCs[ac[1]].Fs_DU[0], int):
                    valid = False
                if len(paths[ac[0]].p3) == 0 and not isinstance(self.DRCs[ac[1]].Fs_RU[0], int):
                    valid = False

            # remove actions that cant be chosen because of link capacity penalty
            if valid:
                for l in paths[ac[0]].p1:
                    if self.continuous_observation_space[self.links_index[l]] - (self.DRCs[ac[1]].bw_BH/self.links_capacity[self.links_index[l]])*100 < 0:
                        valid = False
                for l in paths[ac[0]].p2:
                    if self.continuous_observation_space[self.links_index[l]] - (self.DRCs[ac[1]].bw_MH/self.links_capacity[self.links_index[l]])*100 < 0:
                        valid = False
                for l in paths[ac[0]].p3:
                    if self.continuous_observation_space[self.links_index[l]] - (self.DRCs[ac[1]].bw_FH/self.links_capacity[self.links_index[l]])*100 < 0:
                        valid = False

            # remove actions that cant be chosen given to CRs capacity
            if valid:
                if paths[ac[0]].seq[0]:
                    if self.continuous_observation_space[self.crs_index[paths[ac[0]].seq[0]]] - (self.DRCs[ac[1]].cpu_CU / crs[paths[ac[0]].seq[0]].cpu) * 100 < 0:
                        valid = False
                if paths[ac[0]].seq[1]:
                    if self.continuous_observation_space[self.crs_index[paths[ac[0]].seq[1]]] - (self.DRCs[ac[1]].cpu_DU / crs[paths[ac[0]].seq[1]].cpu) * 100 < 0:
                        valid = False
                if paths[ac[0]].seq[2]:
                    if self.continuous_observation_space[self.crs_index[paths[ac[0]].seq[2]]] - (self.DRCs[ac[1]].cpu_RU / crs[paths[ac[0]].seq[2]].cpu) * 100 < 0:
                        valid = False
            # DELAY PENALTY CHECK
            if valid:
                if paths[ac[0]].delay_p1 > self.DRCs[ac[1]].delay_BH:
                    valid = False
                if paths[ac[0]].delay_p2 > self.DRCs[ac[1]].delay_MH:
                    valid = False
                if paths[ac[0]].delay_p3 > self.DRCs[ac[1]].delay_FH:
                    valid = False

            # MURTI FIXED CU CONSTRAINT
            if valid:
                if paths[ac[0]].seq[1] != 1 and ac[1] == 3:
                    valid = False

            if valid:
                if paths[ac[0]].seq[0] == 0 and paths[ac[0]].seq[1] == 0:
                    valid = False

            if valid:
                acts.append(ac)
        return acts
