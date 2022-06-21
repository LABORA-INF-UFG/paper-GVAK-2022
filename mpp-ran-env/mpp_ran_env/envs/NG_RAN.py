import time
import json
from docplex.mp.model import Model
from docplex.util.environment import get_environment


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

    def __str__(self):
        return "ID: {}\tSEQ: {}\t P1: {}\t P2: {}\t P3: {}\t dP1: {}\t dP2: {}\t dP3: {}".format(self.id, self.seq, self.p1, self.p2, self.p3, self.delay_p1, self.delay_p2, self.delay_p3)


class RC:
    def __init__(self, id, cpu, num_BS):
        self.id = id
        self.cpu = cpu
        self.num_BS = num_BS

    def __str__(self):
        return "ID: {}\tCPU: {}".format(self.id, self.cpu)


class DSG:
    def __init__(self, id, cpu_CU, cpu_DU, cpu_RU, ram_CU, ram_DU, ram_RU, Os_CU, Os_DU, Os_RU, delay_BH, delay_MH,
                 delay_FH, bw_BH, bw_MH, bw_FH):
        self.id = id

        self.cpu_CU = cpu_CU
        self.ram_CU = ram_CU
        self.Os_CU = Os_CU

        self.cpu_DU = cpu_DU
        self.ram_DU = ram_DU
        self.Os_DU = Os_DU

        self.cpu_RU = cpu_RU
        self.ram_RU = ram_RU
        self.Os_RU = Os_RU

        self.delay_BH = delay_BH
        self.delay_MH = delay_MH
        self.delay_FH = delay_FH

        self.bw_BH = bw_BH
        self.bw_MH = bw_MH
        self.bw_FH = bw_FH


class Os:
    def __init__(self, id, O_cpu, O_ram):
        self.id = id
        self.O_cpu = O_cpu
        self.O_ram = O_ram


class RU:
    def __init__(self, id, RC):
        self.id = id
        self.RC = RC

    def __str__(self):
        return "RU: {}\tRC: {}".format(self.id, self.RC)


links = []
capacity = {}
delay = {}
rcs = {}
paths = {}
conj_Os = {}


def read_topology():
    """
    READ TIM TOPOLOGY FILE
    This method read the topology json file and create the main structure that will be used in all model fases
    :rtype: insert in the globals structures the topology information. For that the method has no return
    """
    with open('high_capacity.json') as json_file:
        data = json.load(json_file)

        # create a set of links with delay and capacity read by the json file, stored in a global list "links"
        json_links = data["links"]
        for item in json_links:
            link = json_links[item]
            source = link["source"]
            destination = link["destination"]

            split = str(source["node"]).rsplit('N', 1)
            if source["node"] != "CN":
                source_node = int(split[1])
            else:
                source_node = 0

            split = str(destination["node"]).rsplit('N', 1)
            if destination["node"] != "CN":
                destination_node = int(split[1])
            else:
                destination_node = 0

            # create links full duplex for each link readed by the json file
            capacity[(source_node, destination_node)] = int(str(link["linkCapacity"]))
            delay[(source_node, destination_node)] = float(str(link["LinkDelay"]).replace(',', '.'))
            if (source_node, destination_node) != '':
                links.append((source_node, destination_node))
            # creating links full duplex for each link readed by the json file
            capacity[(destination_node, source_node)] = int(str(link["linkCapacity"]))
            delay[(destination_node, source_node)] = float(str(link["LinkDelay"]).replace(',', '.'))
            if (destination_node, source_node) != '':
                links.append((destination_node, source_node))

        # create and store the set of RC's with RAM and CPU in a global list "rcs"-rc[0] is the core network without CR
        with open('RU_0_1_high.json') as json_file:
            data = json.load(json_file)
            json_nodes = data["nodes"]
            for item in json_nodes:
                split = str(item).rsplit('-', 1)
                RC_id = split[1]
                node = json_nodes[item]
                #node_RAM = node["RAM"]
                node_CPU = node["CPU"]
                rc = RC(int(RC_id), node_CPU, 0)
                rcs[int(RC_id)] = rc
        rcs[0] = RC(0, 0, 0)

        # create a set of paths that are calculated previously by the algorithm implemented in "path_gen.py"
        with open('8_CRs_paths.json') as json_paths_file:
            #read the json file that contain the set of paths
            json_paths_f = json.load(json_paths_file)
            json_paths = json_paths_f["paths"]

            #for each path calculate the id, source (always the core node) and destination
            for item in json_paths:
                path = json_paths[item]
                path_id = path["id"]
                path_source = path["source"]

                if path_source == "CN":
                    path_source = 0

                path_target = path["target"]
                path_seq = path["seq"]

                #calculate the intermediate paths p1, p2 and p3 (that path's correspond to BH, MH and FH respectively)
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
                        sum_delay += float(str(delay[tup_aux]).replace(',', '.'))

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

                #create the path and store at the global dict "paths"
                p = Path(path_id, path_source, path_target, path_seq, list_p1, list_p2, list_p3, delay_p1, delay_p2, delay_p3)
                paths[path_id] = p


def read_topology_500():
    """
    READ TELEFONICA TOPOLOGY FILE
    This method read the topology json file and create the main structure that will be used in all model fases
    :rtype: insert in the globals structures the topology information. For that the method has no return
    """
    with open('hierarchy_2.2_HC_128.json') as json_file:
        data = json.load(json_file)

        # create a set of links with delay and capacity read by the json file, stored in a global list "links"
        json_links = data["links"]
        for item in json_links:
            link = item
            source_node = link["fromNode"]
            destination_node = link["toNode"]

            # create links full duplex for each link readed by the json file
            if source_node < destination_node:
                capacity[(source_node, destination_node)] = link["capacity"]
                delay[(source_node, destination_node)] = link["delay"]
                links.append((source_node, destination_node))

            # creating links full duplex for each link readed by the json file
            else:
                capacity[(destination_node, source_node)] = link["capacity"]
                delay[(destination_node, source_node)] = link["delay"]
                links.append((destination_node, source_node))

        # create and store the set of RC's with RAM and CPU in a global list "rcs"-rc[0] is the core network without CR
        with open('128_nodes_RU_1_HC.json') as json_file:
            data = json.load(json_file)
            json_nodes = data["nodes"]
            for item in json_nodes:
                node = item
                RC_id = node["nodeNumber"]
                #node_RAM = node["RAM"]
                node_CPU = node["cpu"]
                rc = RC(RC_id, node_CPU, 0)
                rcs[RC_id] = rc
        rcs[0] = RC(0, 0, 0)

        # create a set of paths that are calculated previously by the algorithm implemented in "path_gen.py"
        with open('8_CRs_paths.json') as json_paths_file:
            #read the json file that contain the set of paths
            json_paths_f = json.load(json_paths_file)
            json_paths = json_paths_f["paths"]

            #for each path calculate the id, source (always the core node) and destination
            for item in json_paths:
                path = json_paths[item]
                path_id = path["id"]
                path_source = path["source"]

                if path_source == "CN":
                    path_source = 0

                path_target = path["target"]
                path_seq = path["seq"]

                #calculate the intermediate paths p1, p2 and p3 (that path's correspond to BH, MH and FH respectively)
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

                #create the path and store at the global dict "paths"
                p = Path(path_id, path_source, path_target, path_seq, list_p1, list_p2, list_p3, delay_p1, delay_p2, delay_p3)
                paths[path_id] = p


def dsg_structure_500():
    #create the DSG's and the set of DSG's
    #dsg1 = 1 dsg2 = 2, dsg4 = 7 and dsg5 = 8 are DSG's that need 3 RC's
    dsg1 = DSG(1, 0.49, 2.058, 2.352, 0.01, 0.01, 0.01, [1], [2, 3, 4, 5, 6], [7, 8], 10, 10, 0.25, 9.9, 13.2, 42.6)
    dsg2 = DSG(2, 0.98, 1.568, 2.352, 0.01, 0.01, 0.01, [1, 2], [3, 4, 5, 6], [7, 8], 10, 10, 0.25, 9.9, 13.2, 42.6)
    dsg4 = DSG(4, 0.49, 1.225, 3.185, 0.01, 0.01, 0.01, [1], [2, 3, 4, 5], [6, 7, 8], 10, 10, 0.25, 9.9, 13.2, 13.6)
    dsg5 = DSG(5, 0.98, 0.735, 3.185, 0.01, 0.01, 0.01, [1, 2], [3, 4, 5], [6, 7, 8], 10, 10, 0.25, 9.9, 13.2, 13.6)

    # dsg6 = 12 dsg7 = 13 dsg9 = 18 and dsg 10 = 17 are DSG's that need 2 RC's
    # dsg6 = DSG(6, 0, 0.49, 4.41, 0, 0.01, 0.01, [0], [1], [2, 3, 4, 5, 6, 7, 8], 0, 10, 10, 0, 9.9, 13.2)
    # dsg7 = DSG(7, 0, 3, 3.92, 0, 0.01, 0.01, [0], [1, 2], [3, 4, 5, 6, 7, 8], 0, 10, 10, 0, 9.9, 13.2)
    dsg9 = DSG(9, 0, 2.54, 2.354, 0, 0.01, 0.01, [0], [1, 2, 3, 4, 5, 6], [7, 8], 0, 10, 0.25, 0, 9.9, 42.6)
    dsg10 = DSG(10, 0, 1.71, 3.185, 0, 0.01, 0.01, [0], [1, 2, 3, 4, 5], [6, 7, 8], 0, 10, 0.25, 0, 3, 13.6)

    #dsg8 = 19 is the D-RAN split, so need just 1 RC
    # dsg8 = DSG(8, 0, 0, 4.9, 0, 0, 0.01, [0], [0], [1, 2, 3, 4, 5, 6, 7, 8], 0, 0, 10, 0, 0, 9.9)

    #set of dsg's
    dsgs = {1: dsg1, 2: dsg2, 4: dsg4, 5: dsg5, 9:dsg9, 10:dsg10}

    return dsgs


def dsg_structure():
    #create the DSG's and the set of DSG's
    #dsg1 = 1 dsg2 = 2, dsg4 = 7 and dsg5 = 8 are DSG's that need 3 RC's
    dsg1 = DSG(1, 0.49, 2.058, 2.352, 0.01, 0.01, 0.01, [1], [2, 3, 4, 5, 6], [7, 8], 10, 10, 0.25, 3, 5.4, 17.4)
    dsg2 = DSG(2, 0.98, 1.568, 2.352, 0.01, 0.01, 0.01, [1, 2], [3, 4, 5, 6], [7, 8], 10, 10, 0.25, 3, 5.4, 17.4)
    dsg4 = DSG(4, 0.49, 1.225, 3.185, 0.01, 0.01, 0.01, [1], [2, 3, 4, 5], [6, 7, 8], 10, 10, 0.25, 3, 5.4, 5.6)
    dsg5 = DSG(5, 0.98, 0.735, 3.185, 0.01, 0.01, 0.01, [1, 2], [3, 4, 5], [6, 7, 8], 10, 10, 0.25, 3, 5.4, 5.6)

    # dsg6 = 12 dsg7 = 13 dsg9 = 18 and dsg 10 = 17 are DSG's that need 2 RC's
    dsg6 = DSG(6, 0, 0.49, 4.41, 0, 0.01, 0.01, [0], [1], [2, 3, 4, 5, 6, 7, 8], 0, 10, 10, 0, 3, 5.4)
    dsg7 = DSG(7, 0, 3, 3.92, 0, 0.01, 0.01, [0], [1, 2], [3, 4, 5, 6, 7, 8], 0, 10, 10, 0, 3, 5.4)
    dsg9 = DSG(9, 0, 2.54, 2.354, 0, 0.01, 0.01, [0], [1, 2, 3, 4, 5, 6], [7, 8], 0, 10, 0.25, 0, 3, 17.4)
    dsg10 = DSG(10, 0, 1.71, 3.185, 0, 0.01, 0.01, [0], [1, 2, 3, 4, 5], [6, 7, 8], 0, 10, 0.25, 0, 3, 5.6)

    #dsg8 = 19 is the D-RAN split, so need just 1 RC
    dsg8 = DSG(8, 0, 0, 4.9, 0, 0, 0.01, [0], [0], [1, 2, 3, 4, 5, 6, 7, 8], 0, 0, 10, 0, 0, 3)

    #set of dsg's
    #dsgs = {8: dsg8}
    dsgs = {1: dsg1, 2: dsg2, 4: dsg4, 5: dsg5, 6: dsg6, 7: dsg7, 8: dsg8, 9:dsg9, 10:dsg10}

    return dsgs


def ru_location():
    """
    Read TIM topology files
    :return:
    """
    rus = {}
    count = 1
    with open('RU_0_1_low.json') as json_file:
        data = json.load(json_file)

        json_rcs = data["nodes"]

        for item in json_rcs:
            node = json_rcs[item]
            num_rus = node["RU"]
            num_rc = str(item).split('-', 1)[1]

            for i in range(0, num_rus):
                rus[count] = RU(count, int(num_rc))
                count += 1

    return rus


def ru_location_500():
    """
    Read TELEFONICA topology files
    :return:
    """
    rus = {}
    count = 1
    with open('128_nodes_RU_1_HC.json') as json_file:
        data = json.load(json_file)

        json_rcs = data["nodes"]

        for item in json_rcs:
            node = item
            num_rus = node["RU"]
            num_rc = node["nodeNumber"]

            for i in range(0, num_rus):
                rus[count] = RU(count, int(num_rc))
                count += 1

    return rus

dsg_f1 = 0
f1_vars = []
f2_vars = []


def run_NG_RAN_model_fase_1():
    """
    This method uses the topology main structure to calculate the optimal solution of the fase 1
    :rtype: This method returns the optimal value of the fase 1
    """

    print("Running Fase - 1")
    print("-----------------------------------------------------------------------------------------------------------")
    alocation_time_start = time.time()

    # read the topology data at the json file
    read_topology_500()
    # read_topology()

    dsgs = dsg_structure_500()
    # dsgs = dsg_structure()

    rus = ru_location_500()
    # rus = ru_location()

    #print the RU's location
    # for ru in rus:
    #     print(rus[ru])

    #create the set of O's (functional splits)
    # O's(id, O_cpu, O_ram)
    O1 = Os(1, 2, 2)
    O2 = Os(2, 2, 2)
    O3 = Os(3, 2, 2)
    O4 = Os(4, 2, 2)
    O5 = Os(5, 2, 2)
    O6 = Os(6, 2, 2)
    O7 = Os(7, 2, 2)
    O8 = Os(8, 2, 2)

    # dsgs priority (stage 3)
    dsg_p = {1: 4, 2: 1, 4: 6, 5: 5, 6: 10, 7: 9, 8: 25, 9: 7, 10: 8}

    #set of O's
    conj_Os = {1: O1, 2: O2, 3: O3, 4: O4, 5: O5, 6: O6}

    #create the fase 1 model
    mdl = Model(name='NGRAN Problem', log_output=True)

    # mdl.parameters.mip.tolerances.mipgap = 0.015
    #mdl.parameters.mip.tolerances.integrality.set(0)
    #tuple that will be used by the decision variable

    i = [(p, d, b) for p in paths for d in dsgs for b in rus if paths[p].seq[2] == rus[b].RC]

    # Decision variable X
    mdl.x = mdl.binary_var_dict(i, name='x')

    # Fase 1 - Objective Function
    mdl.minimize(mdl.sum(mdl.min(1, mdl.sum(mdl.x[it] for it in i if c in paths[it[0]].seq)) for c in rcs if rcs[c].id != 0) - mdl.sum(
        mdl.sum(mdl.max(0, (mdl.sum(mdl.x[it] for it in i if ((o in dsgs[it[1]].Os_CU and paths[it[0]].seq[0] == rcs[c].id) or (
                    o in dsgs[it[1]].Os_DU and paths[it[0]].seq[1] == rcs[c].id) or (
                                                                          o in dsgs[it[1]].Os_RU and paths[it[0]].seq[
                                                                      2] == rcs[c].id))) - 1)) for o in conj_Os) for c in rcs))

    # Constraint 1 (4)
    for b in rus:
        mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if it[2] == b) == 1, 'unicity')

    # Constrains 1.1 (N)
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].target != rus[it[2]].RC) == 0, 'path')

    #constraint 1.2 (N) quebras de 2 so pode escolher caminhos de 2 quebras
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] != 0 and (it[1] == 6 or it[1] == 7 or it[1] == 8 or it[1] ==9 or it[1] == 10)) == 0, 'dsgs_path_pick')

    #constraint 1.3 (N) quebras de 3 so pode escolher caminhos de 3 quebras
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] == 0 and it[1] != 6 and it[1] != 7 and it[1] != 8 and it[1] != 9 and it[1] != 10) == 0, 'dsgs_path_pick2')

    # constraint 1.4 (N) quebras de 1 so pode escolher caminhos de 1 quebras
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] == 0 and paths[it[0]].seq[1] == 0 and it[1] != 8) == 0, 'dsgs_path_pick3')

    # constraint 1.5 (N) caminhos de 2 RC's nao podem usar D-RAN
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] == 0 and paths[it[0]].seq[1] != 0 and it[1] == 8) == 0, 'dsgs_path_pick4')

    # #constraint 1.6 (N) caminhos devem ir para o RC que esta posicionado o RU
    for ru in rus:
        mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[2] != rus[ru].RC and it[2] == rus[ru].id) == 0)

    # Constraint 2 (5)
    for l in links:
        for k in links:
            if l[0] == k[1] and l[1] == k[0]:
                break
        mdl.add_constraint(mdl.sum(mdl.x[it] * dsgs[it[1]].bw_BH for it in i if l in paths[it[0]].p1) + mdl.sum(mdl.x[it] * dsgs[it[1]].bw_MH for it in i if l in paths[it[0]].p2) + mdl.sum(mdl.x[it] * dsgs[it[1]].bw_FH for it in i if l in paths[it[0]].p3) +
                           mdl.sum(mdl.x[it] * dsgs[it[1]].bw_BH for it in i if k in paths[it[0]].p1) + mdl.sum(mdl.x[it] * dsgs[it[1]].bw_MH for it in i if k in paths[it[0]].p2) + mdl.sum(mdl.x[it] * dsgs[it[1]].bw_FH for it in i if k in paths[it[0]].p3)
                           <=capacity[l], 'links_bw')

    # Constraint 3 (6)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p1) <= dsgs[it[1]].delay_BH, 'delay_req_p1')

    # Constraint 4 (7)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p2) <= dsgs[it[1]].delay_MH, 'delay_req_p2')

    # Constraint 5 (8)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p3 <= dsgs[it[1]].delay_FH), 'delay_req_p3')

    # Constraint 6 (9)
    for c in rcs:
        mdl.add_constraint(mdl.sum(mdl.x[it] * dsgs[it[1]].cpu_CU for it in i if c == paths[it[0]].seq[0]) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].cpu_DU for it in i if c == paths[it[0]].seq[1]) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].cpu_RU for it in i if c == paths[it[0]].seq[2]) <= rcs[c].cpu, 'rcs_cpu_usage')

    # Constraint 7 (9) RAM
    # for c in rcs:
    #     mdl.add_constraint(mdl.sum(mdl.x[it] * dsgs[it[1]].ram_CU for it in i if c == paths[it[0]].seq[0]) + mdl.sum(
    #         mdl.x[it] * dsgs[it[1]].ram_DU for it in i if c == paths[it[0]].seq[1]) + mdl.sum(
    #         mdl.x[it] * dsgs[it[1]].ram_RU for it in i if c == paths[it[0]].seq[2]) <= rcs[c].ram, 'rcs_ram_usage')

    #Teste restricao fase 1 na fase 1
   # mdl.add_constraint(mdl.sum(mdl.min(1, mdl.sum(mdl.x[it] for it in i if c in paths[it[0]].seq)) for c in rcs if rcs[c].id != 0) - mdl.sum(
   #     mdl.sum(mdl.max(0, (mdl.sum(mdl.x[it] for it in i if ((o in dsgs[it[1]].Os_CU and paths[it[0]].seq[0] == rcs[c].id) or (
   #                 o in dsgs[it[1]].Os_DU and paths[it[0]].seq[1] == rcs[c].id) or (
   #                                                                       o in dsgs[it[1]].Os_RU and paths[it[0]].seq[
   #	                                                                   2] == rcs[c].id))) - 1)) for o in conj_Os) for c in rcs) == -95)

    # Teste restricao fase 2 na fase 1
    #mdl.add_constraint(mdl.sum(mdl.min(1, mdl.sum(mdl.x[it] for it in i if it[1] == dsg)) for dsg in dsgs) == 6)

    # Teste restricao fase 3 na 1
    #mdl.add_constraint(mdl.sum(mdl.sum(mdl.x[it] * dsg_p[it[1]] for it in i if it[1] == dsg) for dsg in dsgs) <= 542)

    alocation_time_end = time.time()
    start_time = time.time()
    mdl.solve()
    end_time = time.time()
    print("Stage 1 - Alocation Time: {}".format(alocation_time_end - alocation_time_start))
    print("Stage 1 - Enlapsed Time: {}".format(end_time - start_time))
    for it in i:
        if mdl.x[it].solution_value > 0:
            print("x{} -> {}".format(it, mdl.x[it].solution_value))
            print(paths[it[0]].seq)

    with get_environment().get_output_stream("solution.json") as fp:
        mdl.solution.export(fp, "xml")

    disp_Os = {}

    for rc in rcs:
        disp_Os[rc] = {"O1": 0, "O2": 0, "O3": 0, "O4": 0, "O5": 0, "O6": 0, "O7": 0, "O8": 0}

    for it in i:
        for rc in rcs:
            if mdl.x[it].solution_value == 1:
                if rc in paths[it[0]].seq:
                    seq = paths[it[0]].seq
                    if rc == seq[0]:
                        os = dsgs[it[1]].Os_CU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

                    if rc == seq[1]:
                        os = dsgs[it[1]].Os_DU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

                    if rc == seq[2]:
                        os = dsgs[it[1]].Os_RU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

    print("FO: {}".format(mdl.solution.get_objective_value()))

    for rc in disp_Os:
        print(str(rc) + str(disp_Os[rc]))

    global f1_vars
    for it in i:
        if mdl.x[it].solution_value > 0:
            f1_vars.append(it)

    print(mdl.solution.solved_by)
    print(mdl.solution.solve_details)

    return mdl.solution.get_objective_value()


def run_NG_RAN_model_fase_2(FO_fase_1):
    """
    This method uses the topology main structure to calculate the optimal solution of the fase 2
    :rtype: This method returns the optimal value of the fase 2
    """

    print("Running Fase - 2")
    print("-----------------------------------------------------------------------------------------------------------")
    alocation_time_start = time.time()

    # read the topology data at the json file
    read_topology_500()
    # read_topology()

    # dsgs = dsg_structure()
    dsgs = dsg_structure_500()

    rus = ru_location_500()
    # rus = ru_location()

    # print the RU's location
    # for ru in rus:
    #     print(rus[ru])

    # create the set of O's (functional splits)
    # O's(id, O_cpu, O_ram)
    O1 = Os(1, 2, 2)
    O2 = Os(2, 2, 2)
    O3 = Os(3, 2, 2)
    O4 = Os(4, 2, 2)
    O5 = Os(5, 2, 2)
    O6 = Os(6, 2, 2)
    O7 = Os(7, 2, 2)
    O8 = Os(8, 2, 2)

    # set of O's
    conj_Os = {1: O1, 2: O2, 3: O3, 4: O4, 5: O5, 6: O6}

    # create the fase 1 model
    mdl = Model(name='NGRAN Problem2', log_output=True)

    # tuple that will be used by the decision variable
    i = [(p, d, b) for p in paths for d in dsgs for b in rus if paths[p].seq[2] == rus[b].RC]

    #mdl.add_mip_start(solution_f1)

    # Decision variable X
    mdl.x = mdl.binary_var_dict(i, name='x')

    # mdl.add_mip_start(solution_f1)

    # Fase 2 - Objective Function
    mdl.minimize(mdl.sum(mdl.min(1, mdl.sum(mdl.x[it] for it in i if it[1] == dsg)) for dsg in dsgs))

    # Constraint fase 1
    mdl.add_constraint(mdl.sum(mdl.min(1, mdl.sum(mdl.x[it] for it in i if c in paths[it[0]].seq)) for c in rcs if rcs[c].id != 0) - mdl.sum(mdl.sum(mdl.max(0, (mdl.sum(mdl.x[it] for it in i if ((o in dsgs[it[1]].Os_CU and paths[it[0]].seq[0] == rcs[c].id) or (o in dsgs[it[1]].Os_DU and paths[it[0]].seq[1] == rcs[c].id) or (o in dsgs[it[1]].Os_RU and paths[it[0]].seq[2] == rcs[c].id))) - 1)) for o in conj_Os) for c in rcs) == FO_fase_1)

    # Constraint 1 (4)
    for b in rus:
        mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if it[2] == b) == 1, 'unicity')

    # Constrains 1.1 (N)
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].target != rus[it[2]].RC) == 0, 'path')

    # constraint 1.2 (N) quebras de 2 so pode escolher caminhos de 2 quebras
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] != 0 and (
                it[1] == 6 or it[1] == 7 or it[1] == 8 or it[1] == 9 or it[1] == 10)) == 0, 'dsgs_path_pick')

    # constraint 1.3 (N) quebras de 3 so pode escolher caminhos de 3 quebras
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if
                               paths[it[0]].seq[0] == 0 and it[1] != 6 and it[1] != 7 and it[1] != 8 and it[1] != 9 and
                               it[1] != 10) == 0, 'dsgs_path_pick2')
    # contraint 1.4 (N) quebras de 1 so pode escolher caminhos de 1 quebras
    mdl.add_constraint(
        mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] == 0 and paths[it[0]].seq[1] == 0 and it[1] != 8) == 0,
        'dsgs_path_pick3')

    # contraint 1.5 (N) caminhos de 2 RC's nao podem usar D-RAN
    mdl.add_constraint(
        mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] == 0 and paths[it[0]].seq[1] != 0 and it[1] == 8) == 0,
        'dsgs_path_pick4')

    # #constraint 1.6 (N) caminhos devem ir para o RC que esta posicionado o RU
    for ru in rus:
        mdl.add_constraint(
            mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[2] != rus[ru].RC and it[2] == rus[ru].id) == 0)

    # Constraint 2 (5)
    for l in links:
        for k in links:
            if l[0] == k[1] and l[1] == k[0]:
                break
        mdl.add_constraint(mdl.sum(mdl.x[it] * dsgs[it[1]].bw_BH for it in i if l in paths[it[0]].p1) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].bw_MH for it in i if l in paths[it[0]].p2) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].bw_FH for it in i if l in paths[it[0]].p3) +
                           mdl.sum(mdl.x[it] * dsgs[it[1]].bw_BH for it in i if k in paths[it[0]].p1) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].bw_MH for it in i if k in paths[it[0]].p2) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].bw_FH for it in i if k in paths[it[0]].p3)
                           <= capacity[l], 'links_bw')

    # Constraint 3 (6)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p1) <= dsgs[it[1]].delay_BH, 'delay_req_p1')

    # Constraint 4 (7)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p2) <= dsgs[it[1]].delay_MH, 'delay_req_p2')

    # Constraint 5 (8)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p3 <= dsgs[it[1]].delay_FH), 'delay_req_p3')

    # Constraint 6 (9)
    for c in rcs:
        mdl.add_constraint(
            mdl.sum(mdl.x[it] * dsgs[it[1]].cpu_CU for it in i if c == paths[it[0]].seq[0]) + mdl.sum(
                mdl.x[it] * dsgs[it[1]].cpu_DU for it in i if c == paths[it[0]].seq[1]) + mdl.sum(
                mdl.x[it] * dsgs[it[1]].cpu_RU for it in i if c == paths[it[0]].seq[2]) <= rcs[c].cpu,
            'rcs_cpu_usage')

    # # Constraint 7 (9) RAM
    # for c in rcs:
    #     mdl.add_constraint(
    #         mdl.sum(mdl.x[it] * dsgs[it[1]].ram_CU for it in i if c == paths[it[0]].seq[0]) + mdl.sum(
    #             mdl.x[it] * dsgs[it[1]].ram_DU for it in i if c == paths[it[0]].seq[1]) + mdl.sum(
    #             mdl.x[it] * dsgs[it[1]].ram_RU for it in i if c == paths[it[0]].seq[2]) <= rcs[c].ram,
    #         'rcs_ram_usage')

    warm_start = mdl.new_solution()
    for it in f1_vars:
        warm_start.add_var_value(mdl.x[it], 1)
    #warm_start.set_objective_value(3)
    print(warm_start)

    mdl.add_mip_start(warm_start)

    alocation_time_end = time.time()
    start_time = time.time()
    mdl.solve()
    end_time = time.time()

    print("Stage 2 - Alocation Time: {}".format(alocation_time_end - alocation_time_start))
    print("Stage 2 - Enlapsed Time: {}".format(end_time - start_time))

    for it in i:
        if mdl.x[it].solution_value == 1:
            print("x{} -> {}".format(it, mdl.x[it].solution_value))
            print(paths[it[0]].seq)

    with get_environment().get_output_stream("solution.json") as fp:
        mdl.solution.export(fp, "json")

    disp_Os = {}

    for rc in rcs:
        disp_Os[rc] = {"O1": 0, "O2": 0, "O3": 0, "O4": 0, "O5": 0, "O6": 0, "O7": 0, "O8": 0}

    for it in i:
        for rc in rcs:
            if mdl.x[it].solution_value == 1:
                if rc in paths[it[0]].seq:
                    seq = paths[it[0]].seq
                    if rc == seq[0]:
                        os = dsgs[it[1]].Os_CU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

                    if rc == seq[1]:
                        os = dsgs[it[1]].Os_DU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

                    if rc == seq[2]:
                        os = dsgs[it[1]].Os_RU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

    print("FO: {}".format(mdl.solution.get_objective_value()))

    for rc in disp_Os:
        print(str(rc) + str(disp_Os[rc]))

    global f2_vars
    for it in i:
        if mdl.x[it].solution_value > 0:
            f2_vars.append(it)


    return(mdl.solution.get_objective_value())


def run_NG_RAN_model_fase_3(FO_fase_1, FO_fase_2):
    """
    This method uses the topology main structure to calculate the optimal solution of the fase 3
    :rtype: This method returns the optimal value of the fase 3
    """

    print("Running Fase - 3")
    print("-----------------------------------------------------------------------------------------------------------")
    alocation_time_start = time.time()

    # read the topology data at the json file
    read_topology_500()
    # read_topology()

    # dsgs = dsg_structure()
    dsgs = dsg_structure_500()

    rus = ru_location_500()
    # rus = ru_location()

    # # print the RU's location
    # for ru in rus:
    #     print(rus[ru])

    # create the set of O's (functional splits)
    # O's(id, O_cpu, O_ram)
    O1 = Os(1, 2, 2)
    O2 = Os(2, 2, 2)
    O3 = Os(3, 2, 2)
    O4 = Os(4, 2, 2)
    O5 = Os(5, 2, 2)
    O6 = Os(6, 2, 2)
    O7 = Os(7, 2, 2)
    O8 = Os(8, 2, 2)

    # set of O's
    conj_Os = {1: O1, 2: O2, 3: O3, 4: O4, 5: O5, 6: O6}

    #set of DSG priority
    dsg_p = {1: 4, 2: 1, 4: 6, 5: 5, 6: 10, 7: 9, 8: 25, 9: 7, 10: 8}


    # create the fase 1 model
    mdl = Model(name='NGRAN Problem3', log_output=True)

    # tuple that will be used by the decision variable
    i = [(p, d, b) for p in paths for d in dsgs for b in rus if paths[p].seq[2] == rus[b].RC]

    # Decision variable X
    mdl.x = mdl.binary_var_dict(i, name='x')

    #Fase 3 Objective Function
    mdl.minimize(mdl.sum(mdl.sum(mdl.x[it] * dsg_p[it[1]] for it in i if it[1] == dsg) for dsg in dsgs))

    # Constraint fase 2
    mdl.add_constraint(mdl.sum(mdl.min(1, mdl.sum(mdl.x[it] for it in i if it[1] == dsg)) for dsg in dsgs) == FO_fase_2)

    # Constraint fase 1
    mdl.add_constraint(mdl.sum(mdl.min(1, mdl.sum(mdl.x[it] for it in i if c in paths[it[0]].seq)) for c in rcs if rcs[c].id != 0) - mdl.sum(mdl.sum(mdl.max(0, (mdl.sum(mdl.x[it] for it in i if ((o in dsgs[it[1]].Os_CU and paths[it[0]].seq[0] == rcs[c].id) or (o in dsgs[it[1]].Os_DU and paths[it[0]].seq[1] == rcs[c].id) or (o in dsgs[it[1]].Os_RU and paths[it[0]].seq[2] == rcs[c].id))) - 1)) for o in conj_Os) for c in rcs) == FO_fase_1)

    # Constraint 1 (4)
    for b in rus:
        mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if it[2] == b) == 1, 'unicity')

    # Constrains 1.1 (N)
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].target != rus[it[2]].RC) == 0, 'path')

    # constraint 1.2 (N) quebras de 2 so pode escolher caminhos de 2 quebras
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] != 0 and (
                it[1] == 6 or it[1] == 7 or it[1] == 8 or it[1] == 9 or it[1] == 10)) == 0, 'dsgs_path_pick')

    # constraint 1.3 (N) quebras de 3 so pode escolher caminhos de 3 quebras
    mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if
                               paths[it[0]].seq[0] == 0 and it[1] != 6 and it[1] != 7 and it[1] != 8 and it[1] != 9 and
                               it[1] != 10) == 0, 'dsgs_path_pick2')

    # contraint 1.4 (N) quebras de 1 so pode escolher caminhos de 1 quebras
    mdl.add_constraint(
        mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] == 0 and paths[it[0]].seq[1] == 0 and it[1] != 8) == 0,
        'dsgs_path_pick3')

    # contraint 1.5 (N) caminhos de 2 RC's nao podem usar D-RAN
    mdl.add_constraint(
        mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[0] == 0 and paths[it[0]].seq[1] != 0 and it[1] == 8) == 0,
        'dsgs_path_pick4')

    # #constraint 1.6 (N) caminhos devem ir para o RC que esta posicionado o RU
    for ru in rus:
        mdl.add_constraint(
            mdl.sum(mdl.x[it] for it in i if paths[it[0]].seq[2] != rus[ru].RC and it[2] == rus[ru].id) == 0)

    # Constraint 2 (5)
    for l in links:
        for k in links:
            if l[0] == k[1] and l[1] == k[0]:
                break
        mdl.add_constraint(mdl.sum(mdl.x[it] * dsgs[it[1]].bw_BH for it in i if l in paths[it[0]].p1) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].bw_MH for it in i if l in paths[it[0]].p2) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].bw_FH for it in i if l in paths[it[0]].p3) +
                           mdl.sum(mdl.x[it] * dsgs[it[1]].bw_BH for it in i if k in paths[it[0]].p1) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].bw_MH for it in i if k in paths[it[0]].p2) + mdl.sum(
            mdl.x[it] * dsgs[it[1]].bw_FH for it in i if k in paths[it[0]].p3)
                           <= capacity[l], 'links_bw')

    # Constraint 3 (6)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p1) <= dsgs[it[1]].delay_BH, 'delay_req_p1')

    # Constraint 4 (7)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p2) <= dsgs[it[1]].delay_MH, 'delay_req_p2')

    # Constraint 5 (8)
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p3 <= dsgs[it[1]].delay_FH), 'delay_req_p3')

    # Constraint 6 (9)
    for c in rcs:
        mdl.add_constraint(
            mdl.sum(mdl.x[it] * dsgs[it[1]].cpu_CU for it in i if c == paths[it[0]].seq[0]) + mdl.sum(
                mdl.x[it] * dsgs[it[1]].cpu_DU for it in i if c == paths[it[0]].seq[1]) + mdl.sum(
                mdl.x[it] * dsgs[it[1]].cpu_RU for it in i if c == paths[it[0]].seq[2]) <= rcs[c].cpu,
            'rcs_cpu_usage')

    # Constraint 7 (9) RAM
    # for c in rcs:
    #     mdl.add_constraint(
    #         mdl.sum(mdl.x[it] * dsgs[it[1]].ram_CU for it in i if c == paths[it[0]].seq[0]) + mdl.sum(
    #             mdl.x[it] * dsgs[it[1]].ram_DU for it in i if c == paths[it[0]].seq[1]) + mdl.sum(
    #             mdl.x[it] * dsgs[it[1]].ram_RU for it in i if c == paths[it[0]].seq[2]) <= rcs[c].ram,
    #         'rcs_ram_usage')

    alocation_time_end = time.time()
    start_time = time.time()

    warm_start = mdl.new_solution()
    for it in f2_vars:
        warm_start.add_var_value(mdl.x[it], 1)
    #warm_start.set_objective_value(3)
    print(warm_start)

    mdl.add_mip_start(warm_start)

    mdl.solve()
    end_time = time.time()
    print("Stage 3 - Alocation Time: {}".format(alocation_time_end - alocation_time_start))
    print("Stage 3 - Enlapsed Time: {}".format(end_time - start_time))

    for it in i:
        if mdl.x[it].solution_value == 1:
            print("x{} -> {}".format(it, mdl.x[it].solution_value))
            print(paths[it[0]].seq)

    with get_environment().get_output_stream("solution.json") as fp:
        mdl.solution.export(fp, "json")

    disp_Os = {}

    for rc in rcs:
        disp_Os[rc] = {"O1": 0, "O2": 0, "O3": 0, "O4": 0, "O5": 0, "O6": 0, "O7": 0, "O8": 0}

    for it in i:
        for rc in rcs:
            if mdl.x[it].solution_value == 1:
                if rc in paths[it[0]].seq:
                    seq = paths[it[0]].seq
                    if rc == seq[0]:
                        os = dsgs[it[1]].Os_CU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

                    if rc == seq[1]:
                        os = dsgs[it[1]].Os_DU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

                    if rc == seq[2]:
                        os = dsgs[it[1]].Os_RU
                        for o in os:
                            if o != 0:
                                dct = disp_Os[rc]
                                dct["O{}".format(o)] += 1
                                disp_Os[rc] = dct

    print("FO: {}".format(mdl.solution.get_objective_value()))

    for rc in disp_Os:
        print(str(rc) + str(disp_Os[rc]))


if __name__ == '__main__':
    start_all = time.time()

    FO_fase_1 = run_NG_RAN_model_fase_1()
    FO_fase_2 = run_NG_RAN_model_fase_2(FO_fase_1)
    run_NG_RAN_model_fase_3(FO_fase_1, FO_fase_2)

    end_all = time.time()

    print("TOTAL TIME: {}".format(end_all - start_all))
