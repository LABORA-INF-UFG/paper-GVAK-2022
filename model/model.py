# -*- coding: utf-8 -*-
import time
import json
import numpy as np

#from docplex.mp.model import Model
nodes_file = '../topology/topo_4_nodes_hier.json'
links_file= '../topology/topo_4_links_hier.json'
paths_file = '../topology/paths_4_hier.json'


class Path:
    def __init__(self, id, source, target, seq, p1, p2, p3, delay_p1, delay_p2, delay_p3):
        self.id = id
        self.source = source
        self.target = target
        self.seq = seq
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.delay_p1 = delay_p1
        self.delay_p2 = delay_p2
        self.delay_p3 = delay_p3
        self.max_delay = np.max([delay_p1, delay_p2, delay_p3])

    def __str__(self):
        return "ID: {}\tSEQ: {}\t P1: {}\t P2: {}\t P3: {}\t dP1: {}\t dP2: {}\t dP3: {}".format(self.id, self.seq,
                                                                                                 self.p1, self.p2,
                                                                                                 self.p3, self.delay_p1,
                                                                                                 self.delay_p2,
                                                                                                 self.delay_p3)


class CR:
    def __init__(self, id, cpu, num_BS, rus:None):
        self.id = id
        self.cpu = cpu
        self.num_BS = num_BS
        self.rus = rus

    def __str__(self):
        return "ID: {}\tCPU: {}".format(self.id, self.cpu)


class DRC:
    def __init__(self, id, cpu_CU, cpu_DU, cpu_RU, ram_CU, ram_DU, ram_RU, Fs_CU, Fs_DU, Fs_RU, delay_BH, delay_MH,
                 delay_FH, bw_BH, bw_MH, bw_FH, q_CRs, id_table):
        self.id = id
        # real DRC id according to article tables
        self.id_table = id_table

        self.cpu_CU = cpu_CU
        self.ram_CU = ram_CU
        self.Fs_CU = Fs_CU

        self.cpu_DU = cpu_DU
        self.ram_DU = ram_DU
        self.Fs_DU = Fs_DU

        self.cpu_RU = cpu_RU
        self.ram_RU = ram_RU
        self.Fs_RU = Fs_RU

        # in ms
        self.delay_BH = delay_BH
        self.delay_MH = delay_MH
        self.delay_FH = delay_FH

        self.bw_BH = bw_BH
        self.bw_MH = bw_MH
        self.bw_FH = bw_FH

        self.q_CRs = q_CRs

        #setting max values
        self.max_cpu  = np.max([cpu_CU, cpu_DU, cpu_RU])
        self.max_ram  = np.max([ram_CU, ram_DU, ram_RU])
        self.max_delay= np.max([delay_BH, delay_MH, delay_FH])
        self.max_BW   = np.max([bw_BH, bw_MH, bw_FH])


class FS:
    def __init__(self, id, f_cpu, f_ram):
        self.id = id
        self.f_cpu = f_cpu
        self.f_ram = f_ram


class RU:
    def __init__(self, id, CR):
        self.id = id
        self.CR = CR

    def __str__(self):
        return "RU: {}\tCR: {}".format(self.id, self.CR)


# Global vars
links = []
capacity = {}
delay = {}
crs = {}
paths = {}
conj_Fs = {}


def read_topology():
    """
    READ T1 TOPOLOGY FILE
    Implements the topology from reading the json file and creates the main structure that is used by the stages of the model.
    :rtype: Inserts topology data into global structures, so the method has no return
    """
    with open(links_file) as json_file:
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
                # add this to TIM topo
                # capacity[(destination_node, source_node)] = link["capacity"]
                # delay[(destination_node, source_node)] = link["delay"]
                # links.append((destination_node, source_node))

            # Creates links full duplex for each link in the json file
            else:
                capacity[(destination_node, source_node)] = link["capacity"]
                delay[(destination_node, source_node)] = link["delay"]
                links.append((destination_node, source_node))
                # add this to TIM topo
                # capacity[(source_node, destination_node)] = link["capacity"]
                # delay[(source_node, destination_node)] = link["delay"]
                # links.append((source_node, destination_node))

        # Creates the set of CRs with RAM and CPU in a global list "crs" -- cr[0] is the network Core node
        with open(nodes_file) as json_file:
            data = json.load(json_file)
            json_nodes = data["nodes"]
            for item in json_nodes:
                node = item
                CR_id = node["nodeNumber"]
                # node_RAM = node["RAM"]
                node_CPU = node["cpu"]
                cr = CR(CR_id, node_CPU, 0)
                crs[CR_id] = cr
        crs[0] = CR(0, 0, 0)

        # Creates the set of previously calculated paths "8_CRs_paths.json". -- the algorithm used to calculate the paths is the k-shortest paths algorithm.
        with open(paths_file) as json_paths_file:
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


def DRC_structure():
    # IMPLEMENTS T2 Topology DRCs
    # Implements the DRCs defined with cpu usage, ram usage, VNFs splits and network resources requirements, for T2 Topology
    # :rtype: Dict with the DRCs informations

    # Creates the DRCs
    # DRCs MAP (id: DRC): 1 = DRC1, 2 = DRC2, 4 = DRC7 and 5 = DRC8 -- DRCs with 3 independents CRs [CU]-[DU]-[RU]
    DRC1 = DRC(1, 0.49, 2.058, 2.352, 0.01, 0.01, 0.01, ['f8'], ['f7', 'f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'], 10,
               10, 0.25, 9.9, 13.2, 42.6, 3)
    DRC2 = DRC(2, 0.98, 1.568, 2.352, 0.01, 0.01, 0.01, ['f8', 'f7'], ['f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'], 10,
               10, 0.25, 9.9, 13.2, 42.6, 3)
    DRC4 = DRC(7, 0.49, 1.225, 3.185, 0.01, 0.01, 0.01, ['f8'], ['f7', 'f6', 'f5', 'f4', 'f3'], ['f2', 'f1', 'f0'], 10,
               10, 0.25, 9.9, 13.2, 13.6, 3)
    DRC5 = DRC(8, 0.98, 0.735, 3.185, 0.01, 0.01, 0.01, ['f8', 'f7'], ['f6', 'f5', 'f4', 'f3'], ['f2', 'f1', 'f0'], 10,
               10, 0.25, 9.9, 13.2, 13.6, 3)

    # DRCs MAP (id: DRC): 6 = DRC12, 7 = DRC13, 9 = DRC18 and 10 = DRC17  -- DRCs with 2 CRs [CU/DU]-[RU] or [CU]-[DU/RU]
    DRC6 = DRC(12, 0, 0.49, 4.41, 0, 0.01, 0.01, [0], ['f8'], ['f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'], 0, 10,
               10, 0, 9.9, 13.2, 2)
    DRC7 = DRC(13, 0, 3, 3.92, 0, 0.01, 0.01, [0], ['f8', 'f7'], ['f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'], 0, 10, 10,
               0, 9.9, 13.2, 2)
    DRC9 = DRC(18, 0, 2.54, 2.354, 0, 0.01, 0.01, [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'], 0, 10,
               0.25, 0, 9.9, 42.6, 2)
    DRC10 = DRC(17, 0, 1.71, 3.185, 0, 0.01, 0.01, [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3'], ['f2', 'f1', 'f0'], 0, 10,
                0.25, 0, 3, 13.6, 2)

    # DRCs MAP (id: DRC): 8 = DRC19 -- D-RAN with 1 CR [CU/DU/RU]
    DRC8 = DRC(18, 0, 0, 4.9, 0, 0, 0.01, [0], [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'], 0, 0, 10, 0,
               0, 9.9, 1)

    # Creates the set of DRCs
    DRCs = {1: DRC1, 2: DRC2, 4: DRC4, 5: DRC5, 6: DRC6, 7: DRC7, 8: DRC8, 9: DRC9, 10: DRC10}

    return DRCs



def RU_location():
    """
    SET THE T2 TOPOLOGY RUs
    Reads the T2 Topology file and define the RUs locations
    :return: Dict with RUs information
    """

    rus = {}
    count = 1
    # Reads the topology file with RUs locations
    with open(nodes_file) as json_file:
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


# global vars that manages the warm_start for stage 2 and stage 3
DRC_f1 = 0
f1_vars = []
f2_vars = []


def run_stage_1():
    """
    RUN THE STAGE 1
    This method uses the topology main structure to calculate the optimal solution of the Stage 1
    :rtype: (int) This method returns the Objective Function value of the Stage 1
    """

    print("Running Stage - 1")
    print("------------------------------------------------------------------------------------------------------------")
    alocation_time_start = time.time()

    read_topology()
    DRCs = DRC_structure()
    rus = RU_location()

    # Creates the set of Fs (functional splits)
    # Fs(id, f_cpu, f_ram)
    F1 = FS('f8', 2, 2)
    F2 = FS('f7', 2, 2)
    F3 = FS('f6', 2, 2)
    F4 = FS('f5', 2, 2)
    F5 = FS('f4', 2, 2)
    F6 = FS('f3', 2, 2)
    F7 = FS('f2', 2, 2)
    F8 = FS('f1', 2, 2)
    F9 = FS('f0', 2, 2)
    conj_Fs = {'f8': F1, 'f7': F2, 'f6': F3, 'f5': F4, 'f4': F5, 'f3': F6, 'f2': F7}

    # Creates the Stage 1 model
    #mdl = Model(name='NGRAN Problem', log_output=True)
    # Set the GAP value (the model execution stop when GAP hits the value -- Default: 0%)
    # Tuple used by the decision variable management
    i = [(p, d, b) for p in paths for d in DRCs for b in rus if paths[p].seq[2] == rus[b].CR]
    acts = [len(paths), len(DRCs), len(rus)]
    for p in paths:
        print(p)
    print(i)


    return None


if __name__ == '__main__':
    start_all = time.time()

    FO_Stage_1 = run_stage_1()
    #FO_Stage_2 = run_stage_2(FO_Stage_1)
    #run_stage_3(FO_Stage_1, FO_Stage_2)

    end_all = time.time()

    print("TOTAL TIME: {}".format(end_all - start_all))
