from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class ProviderCapabilities(BaseModel):
    supports_circuits: bool = False
    supports_bqm: bool = False
    supports_cqm: bool = False
    supports_hobo: bool = False
    supports_sampling: bool = False
    supports_hybrid: bool = False
    supports_real_hardware: bool = False


class ProviderResult(BaseModel):
    job_id: str
    status: str
    raw_result: dict
    metadata: dict = Field(default_factory=dict)


class BaseProvider(ABC):
    name: str
    capabilities: ProviderCapabilities

    @abstractmethod
    def submit(self, problem: dict, solver_config: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def run(self, experiment: dict) -> ProviderResult:
        raise NotImplementedError

    @abstractmethod
    def get_result(self, job_id: str) -> ProviderResult:
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def estimate_cost(self, problem: dict, solver_config: dict) -> float:
        raise NotImplementedError
