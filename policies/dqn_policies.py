from stable_baselines.deepq.policies import FeedForwardPolicy
from stable_baselines.deepq.policies import LnMlpPolicy

# Custom MLP policy of 10 layers of size 32 each
class CustomDQNPolicy(FeedForwardPolicy):
    def __init__(self, *args, **kwargs):
        super(CustomDQNPolicy, self).__init__(*args, **kwargs,
                                           layers=[256, 256],
                                           layer_norm=False,
                                           feature_extraction="mlp")

class CustomLnMlpPolicy(LnMlpPolicy):
    def __init__(self, *args, **kwargs):
        super(CustomLnMlpPolicy, self).__init__(*args, **kwargs,
                                                layers=[256, 256, 256])