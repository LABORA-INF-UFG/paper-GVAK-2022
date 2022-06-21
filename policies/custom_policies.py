from stable_baselines.common.policies import FeedForwardPolicy
from stable_baselines.common.policies import MlpPolicy


class CustomMlpPolicy(MlpPolicy):
    def __init__(self, *args, **kwargs):
        super(CustomMlpPolicy, self).__init__(*args, **kwargs,
                                                layers=[256, 256])