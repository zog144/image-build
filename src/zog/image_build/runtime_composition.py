"""Select whole package outputs for immutable native-runtime refreshes."""
from .metadata import Package, order


def select(definitions, targets, inherited, built):
    """Retain base membership, replacing same-name outputs without overlaying roots.

    Explicit assembly targets carry inherited packages without changing recipe
    dependency edges. Build-only fixtures remain outside the runtime closure.
    """
    definitions = dict(definitions)
    for name in inherited:
        definitions.setdefault(name, Package(name, (), (), (), {}, {}, (), {}))
    targets = list(dict.fromkeys((*inherited, *targets)))
    selected = order(definitions, targets, runtime_only=True)
    return definitions, targets, {name: built[name] for name in selected}
