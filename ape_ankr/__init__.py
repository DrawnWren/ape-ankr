from ape import plugins

from .providers import Ankr

NETWORKS = [
    ("polygon","mainnet"),
    ("fantom","opera"),
    ("solana","mainnet"),
    ("bsc","mainnet"),
]



@plugins.register(plugins.ProviderPlugin)
def providers():
    for ecosystem_name, network_name in NETWORKS:
        yield ecosystem_name, network_name, Ankr
