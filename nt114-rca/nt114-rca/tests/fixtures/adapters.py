"""Adapters for driver tests. Module-level so worker processes can unpickle them."""
from rca.adapters.rcaeval import RCAEvalAdapter


class RaisingAdapter(RCAEvalAdapter):
    """Raises while normalizing the cart case, as a broken adapter would."""

    def normalize(self, inc, modality, tinfo, smap, ctx, findings):
        if "cartservice_delay" in inc.source_incident_key and modality == "logs":
            raise RuntimeError("boom in logs")
        yield from super().normalize(inc, modality, tinfo, smap, ctx, findings)
