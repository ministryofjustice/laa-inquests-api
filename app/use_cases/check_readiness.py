from app.ports.check_readiness_port import CheckReadinessPort


class CheckReadinessUseCase:
    def __init__(self, readiness_port: CheckReadinessPort) -> None:
        self.readiness_port = readiness_port

    def execute(self) -> None:
        self.readiness_port.check()
