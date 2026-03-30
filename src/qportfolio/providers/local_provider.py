from qportfolio.providers.base import BaseProvider, ProviderCapabilities, ProviderResult


class LocalSimulatorProvider(BaseProvider):
    name = "local_simulator"
    capabilities = ProviderCapabilities(
        supports_circuits=True,
        supports_bqm=True,
        supports_sampling=True,
    )

    def submit(self, problem: dict, solver_config: dict) -> str:
        _ = (problem, solver_config)
        return "local-job-001"

    def run(self, experiment: dict) -> ProviderResult:
        return ProviderResult(job_id="local-job-001", status="completed", raw_result=experiment)

    def get_result(self, job_id: str) -> ProviderResult:
        return ProviderResult(job_id=job_id, status="completed", raw_result={})

    def get_metadata(self) -> dict:
        return {"provider": self.name, "capabilities": self.capabilities.model_dump()}

    def estimate_cost(self, problem: dict, solver_config: dict) -> float:
        _ = (problem, solver_config)
        return 0.0
