from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Tuple

class BaseEcosystemProvider(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def detect_project(self, path: Path) -> bool:
        pass

    @abstractmethod
    def parse_declared(self, path: Path) -> Dict[str, str]:
        pass

    @abstractmethod
    def get_global_installed(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def find_reclaimable_bloat(self, path: Path) -> List[Tuple[Path, int]]:
        pass
