import gym
from stable_baselines import DQN, A2C, PPO2
import time
from policies.dqn_policies import CustomLnMlpPolicy
import numpy as np
import json
import random
from numpyencoder import NumpyEncoder
from stable_baselines.deepq.policies import MlpPolicy
from stable_baselines.common.policies import MlpPolicy

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
for i in range(2, 257):
    C7[str(i)] = 1

C = C7
Cs = "C7"

kwargs = {
    'topology': '8',
    'nactions': [213],
    'demand_per_RU': C
}

env = gym.make('mpp_ran_env:mpp-ran-v0', **kwargs)

model = PPO2(MlpPolicy, env, verbose=1)
# model = DQN(CustomLnMlpPolicy, env, verbose=2, gamma=0.7, learning_rate=7e-3, prioritized_replay=True, exploration_fraction=0.4)


def new_training(time_steps):
    start_time = time.time()
    print("Iniciando treino com {} time steps".format(int(time_steps)))

    # model.load_parameters("trained_models/topo_{}_{}K-PPO2".format(kwargs['topology'], int((time_steps)/1000)))

    model.learn(total_timesteps=time_steps)

    end_time = time.time()
    model.save("trained_models/topo_{}_{}K-PPO2_learning_curve".format(kwargs['topology'], int(time_steps / 1000)))

    print("Modelo treinado com {} timesteps".format(time_steps))
    print("Tempo de treinamento = {}".format(end_time - start_time))


def evaluation(time_steps):
    obs = env.reset()
    end_ep = False
    acts_det = []
    history = {}
    model = PPO2.load("trained_models/topo_{}_{}K-PPO2".format(kwargs['topology'], int(time_steps / 1000)))

    start_time = time.time()

    while not end_ep:
        ac, _ = model.predict(obs, deterministic=True)
        obs, rw, end_ep, _ = env.step_validation(ac)
        acts_det.append(ac)
        print("Action {} - rw = {}".format(ac, rw))
    FO1 = rw * -1
    print("FO = {}".format(FO1))

    obs = env.reset()
    end_ep = False
    acts_ndet = []

    while not end_ep:
        ac, _ = model.predict(obs, deterministic=False)
        obs, rw, end_ep, _ = env.step_validation(ac)
        acts_ndet.append(ac)
        # print("N deterministic Action {} - rw = {}".format(ac, rw))

    FO2 = rw * -1
    print("FO = {}".format(FO2))

    end_time = time.time()

    history[int(time_steps / 1000)] = {'deterministic': acts_det, 'n_deterministic': acts_ndet}

    print("------------------------------------------------------------------------------------")
    print("Tempo de resposta = {}".format(end_time - start_time))

    with open('results/20_CRs/{}k_timesteps/{}.json'.format(int(time_steps/1000), Cs), 'w') as fp:
        json.dump({Cs: C, "FO1": FO1, "FO2": FO2, "time": end_time - start_time}, fp)


if __name__ == '__main__':
    new_training(time_steps=500000)
    # evaluation(time_steps=500000)
