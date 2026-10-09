from abc import ABC, abstractmethod
from typing import Any
from .schema import Incident

class BaseAnalyzer(ABC):
    @property
    @abstractmethod
    def layer(self) -> str:
        """The observability layer this analyzer is responsible for (e.g., 'data_drift')."""
        pass

    @abstractmethod
    def analyze(self, payload: Any) -> Incident:
        """Analyze the payload and return an RCA Incident report."""
        pass
