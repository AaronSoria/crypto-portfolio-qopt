from qportfolio.providers.base import BaseProvider, ProviderCapabilities, ProviderResult


class QiskitProvider(BaseProvider):
    name = "qiskit"
    capabilities = ProviderCapabilities(
        supports_circuits=True,
        supports_sampling=True,
        supports_real_hardware=True,
    )

    def submit(self, problem: dict, solver_config: dict) -> str:
        _ = (problem, solver_config)
        return "qiskit-job-pending"

    def run(self, experiment: dict) -> ProviderResult:
        return ProviderResult(job_id="qiskit-job-pending", status="stub", raw_result=experiment)

    def get_result(self, job_id: str) -> ProviderResult:
        return ProviderResult(job_id=job_id, status="stub", raw_result={})

    def get_metadata(self) -> dict:
        return {"provider": self.name, "capabilities": self.capabilities.model_dump()}

    def estimate_cost(self, problem: dict, solver_config: dict) -> float:
        _ = (problem, solver_config)
        return 0.0
