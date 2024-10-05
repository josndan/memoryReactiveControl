import gymnasium as gym
import torch
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.type_aliases import TensorDict

from featureextractors.agentidfeatureextractor import AgentIdFeatureExtractor
from featureextractors.gridfeatureextractor import GridFeatureExtractor
from featureextractors.itemsfeatureextractor import ItemsFeatureExtractor


class GridVerseFeatureExtractor(BaseFeaturesExtractor):
    def __init__(
            self,
            observation_space: gym.vector.utils.spaces.Dict,
            config: dict,
    ) -> None:
        # TODO we do not know features-dim here before going over all the items, so put something there. This is dirty!
        super().__init__(observation_space, features_dim=1)

        # Grid
        grid_subspace = observation_space.spaces['grid']
        if not isinstance(grid_subspace, gym.spaces.Box):
            raise ValueError(
                f"Expected observation space to be of type 'Box' for grid subspace, but got: {type(grid_subspace)}")
        # The i,j is grid co-ordinates. the last index is the grid object index type; for now we are ignoring the color and items in the grid
        number_of_grid_cell_types = grid_subspace.high[..., 0].max() - grid_subspace.low[..., 0].min() + 1
        number_of_grid_cell_states_per_cell_type = grid_subspace.high[..., 1].max() - grid_subspace.low[
            ..., 1].min() + 1
        number_of_grid_colors = grid_subspace.high[..., 2].max() - grid_subspace.low[..., 2].min() + 1

        ndim = grid_subspace.high.ndim
        # ndim = 3 means(x, y, [object,color,item]])
        if ndim == 3:
            self.grid_feature_extractor = GridFeatureExtractor(number_of_grid_cell_types,
                                                               number_of_grid_cell_states_per_cell_type,
                                                               number_of_grid_colors,
                                                               config['grid_encoder'], grid_subspace)

        else:
            raise ValueError(f"Unsupported grid tensor shape: {grid_subspace.shape}")

        # Agent ID
        agent_id_subspace = observation_space.spaces['agent_id_grid']
        self.agent_id_feature_extractor = AgentIdFeatureExtractor(agent_id_subspace,
                                                                  config['agent_id_encoder'])

        # Items
        item_subspace = observation_space.spaces['item']
        if not isinstance(item_subspace, gym.spaces.Box):
            raise ValueError(
                f"Expected observation space to be of type 'Box' for item subspace, but got: {type(grid_subspace)}")
        number_of_item_types = item_subspace.high[0] - item_subspace.low[0] + 1
        number_of_item_states = item_subspace.high[1] - item_subspace.low[1] + 1
        number_of_item_colors = item_subspace.high[2] - item_subspace.low[2] + 1

        self.items_feature_extractor = ItemsFeatureExtractor(number_of_item_types, number_of_item_states,
                                                             number_of_item_colors,
                                                             config['items_encoder'], item_subspace)

        # Update the features dim manually
        self._features_dim = config['grid_encoder']['output_dim'] + config['agent_id_encoder']['output_dim'] + \
                             config['items_encoder']['layers'][-1]

    def forward(self, observations: TensorDict) -> torch.Tensor:
        grid_features = self.grid_feature_extractor(torch.tensor(observations['grid'], dtype=torch.int))
        agent_id_features = self.agent_id_feature_extractor(
            torch.tensor(observations['agent_id_grid'], dtype=torch.int))
        items_features = self.items_feature_extractor(torch.tensor(observations['item'], dtype=torch.int))

        concat_features = torch.cat([grid_features, agent_id_features, items_features], dim=1)

        return concat_features