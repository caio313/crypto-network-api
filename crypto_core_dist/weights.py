from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreWeights:
    safety: float = 0.35
    reliability: float = 0.3
    cost: float = 0.25
    speed: float = 0.1

    def validate(self) -> bool:
        total = self.safety + self.reliability + self.cost + self.speed
        return abs(total - 1.0) < 0.001


DEFAULT_WEIGHTS = ScoreWeights()
