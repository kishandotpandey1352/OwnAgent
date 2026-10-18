class ModelProviderError(RuntimeError):
    """Base error for model-provider failures."""


class ModelProviderNotFoundError(
    ModelProviderError
):
    """Requested model provider is not registered."""


class ModelProviderAlreadyRegisteredError(
    ModelProviderError
):
    """Provider ID is already registered."""


class ModelProviderContractError(
    ModelProviderError
):
    """Provider returned data that violates the model contract."""


class ModelProviderInvocationError(
    ModelProviderError
):
    """Provider invocation failed."""