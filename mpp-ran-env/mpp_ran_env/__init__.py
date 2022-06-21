from gym.envs.registration import register

register(
    id='mpp-ran-v0',
    entry_point='mpp_ran_env.envs:MppRanEnv',
)
