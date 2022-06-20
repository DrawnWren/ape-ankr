import os
from typing import Dict

from ape.api import UpstreamProvider, Web3Provider
from ape.exceptions import ContractLogicError, ProviderError, VirtualMachineError
from web3 import HTTPProvider, Web3  # type: ignore
from web3.exceptions import ContractLogicError as Web3ContractLogicError
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from web3.middleware import geth_poa_middleware

_SUPPORTED_NETWORKS = ("polygon", "opera", "solana", "bsc")


class AnkrProviderError(ProviderError):
    """
    An error raised by the Ankr provider plugin.
    """

class UnsupportedNetworkError(AnkrProviderError):
    def __init__(self):
        env_var_str = ", ".join([f"${n}" for n in _SUPPORTED_NETWORKS])
        super().__init__(f"Must set one of {env_var_str}")


class Ankr(Web3Provider, UpstreamProvider):
    network_uris: Dict[str, str] = {
        "polygon": "https://polygon-rpc.com",
        "opera": "http://rpc.ftm.tools",
        "solana": "https://solana.public-rpc.com",
        "bsc": "https://bscrpc.com"
    }

    @property
    def uri(self) -> str:
        network_name = self.network.name
        if network_name in self.network_uris:
            return self.network_uris[network_name]
        raise UnsupportedNetworkError()

    @property
    def connection_str(self) -> str:
        return self.uri

    def connect(self):
        self._web3 = Web3(HTTPProvider(self.uri))
        if self._web3.eth.chain_id in (4, 5, 42):
            self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self._web3.eth.set_gas_price_strategy(rpc_gas_price_strategy)

    def disconnect(self):
        self._web3 = None  # type: ignore

    def get_virtual_machine_error(self, exception: Exception) -> VirtualMachineError:
        if not hasattr(exception, "args") or not len(exception.args):
            return VirtualMachineError(base_err=exception)

        args = exception.args
        message = args[0]
        if (
            not isinstance(exception, Web3ContractLogicError)
            and isinstance(message, dict)
            and "message" in message
        ):
            # Is some other VM error, like gas related
            return VirtualMachineError(message=message["message"])

        elif not isinstance(message, str):
            return VirtualMachineError(base_err=exception)

        # If get here, we have detected a contract logic related revert.
        message_prefix = "execution reverted"
        if message.startswith(message_prefix):
            message = message.replace(message_prefix, "")

            if ":" in message:
                # Was given a revert message
                message = message.split(":")[-1].strip()
                return ContractLogicError(revert_message=message)
            else:
                # No revert message
                return ContractLogicError()

        return VirtualMachineError(message=message)
