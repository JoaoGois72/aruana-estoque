from .material import Material
from .categoria import Categoria
from .solicitacao import Solicitacao
from .solicitacao_item import SolicitacaoItem
from .entrada import Entrada
from .entrada_item import EntradaItem
from .fornecedor import Fornecedor
from .departamento import Departamento
from .user import User  # MUITO IMPORTANTE

__all__ = [
    "Material",
    "Categoria",
    "Solicitacao",
    "SolicitacaoItem",
    "Entrada",
    "EntradaItem",
    "Fornecedor",
    "User"
]