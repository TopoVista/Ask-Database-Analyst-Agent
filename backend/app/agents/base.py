from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

from app.services.llm_service import LLMService


class BaseAgent(ABC):
    def __init__(self, llm_service: LLMService) -> None:
        self.llm = llm_service
        self.logger = structlog.get_logger(agent=self.__class__.__name__)

    @abstractmethod
    async def run(self, *args, **kwargs):
        raise NotImplementedError

