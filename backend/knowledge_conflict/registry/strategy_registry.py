import logging
from ..exceptions.exceptions import CandidateGenerationException

logger = logging.getLogger('enterprise')

class StrategyRegistry:
    """
    Registry for managing candidate pairing strategy classes,
    allowing strategies to be dynamically resolved based on rules configurations.
    """
    _registry = {}

    @classmethod
    def register(cls, name: str, strategy_class):
        """Register a pairing strategy."""
        cls._registry[name] = strategy_class
        logger.info(f"Registered pairing strategy: {name}")

    @classmethod
    def get_strategy(cls, name: str):
        """Retrieve strategy class by name."""
        if name not in cls._registry:
            raise CandidateGenerationException(f"Strategy {name} is not registered.")
        return cls._registry[name]

    @classmethod
    def get_active_strategies(cls, rules_config: dict) -> list:
        """
        Instantiate and return list of strategy instances that are enabled in configuration.
        """
        active_instances = []
        strategies_config = rules_config.get("strategies", {})
        
        for name, config in strategies_config.items():
            if config.get("enabled", False):
                if name in cls._registry:
                    strategy_class = cls._registry[name]
                    active_instances.append(strategy_class(config))
                else:
                    logger.warning(f"Strategy {name} is enabled in config but not registered in registry.")
                    
        return active_instances
