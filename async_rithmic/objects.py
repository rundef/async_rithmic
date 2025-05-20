import random
from dataclasses import dataclass
from typing import Literal


@dataclass
class RetrySettings:
    max_retries: int
    timeout: float
    jitter_range: tuple = None


@dataclass
class ReconnectionSettings:
    max_retries: int | None = None
    backoff_type: Literal["constant", "linear", "exponential"] = "linear"
    interval: float = 10
    max_delay: float = None
    jitter_range: tuple = None

    def get_delay(self, attempt: int) -> float:
        if self.backoff_type == "constant":
            delay = self.interval

        elif self.backoff_type == "linear":
            delay = min(self.interval * attempt, self.max_delay)

        elif self.backoff_type == "exponential":
            delay = min(self.interval ** attempt, self.max_delay)

        else:
            raise ValueError(f"Unknown backoff_type: {self.backoff_type}")

        if self.jitter_range is not None:
            # Adding jitter to backoff helps prevent the "thundering herd" problem,
            # where multiple clients (e.g., 4 connections) retry at the exact same intervals.
            # By introducing randomness, we reduce the chance that all connections
            # attempt to reconnect at the same time, avoiding load spikes on the server.
            jitter = random.uniform(*self.jitter_range)
            delay += jitter

        return delay
