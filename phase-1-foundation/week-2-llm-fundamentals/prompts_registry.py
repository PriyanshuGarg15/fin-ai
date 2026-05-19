from dataclasses import dataclass
import importlib


@dataclass
class PromptVersion:
    version: str
    description: str
    system_prompt: str
    module_path: str


class PromptsRegistry:
    def __init__(self):
        self._registry: dict[str, PromptVersion] = {}

    def add_prompt(self, name: str, module_path: str):
        module = importlib.import_module(module_path)
        prompt_version = PromptVersion(
            version=module.VERSION,
            description=module.DESCRIPTION,
            system_prompt=module.SYSTEM_PROMPT,
            module_path=module_path,
        )
        self._registry[name] = prompt_version

    def get(self, name: str) -> PromptVersion:
        if name not in self._registry:
            raise KeyError(f"Prompt '{name}' not found in registry")
        return self._registry[name]

    def list(self) -> list[dict]:
        return [
            {
                "name": name,
                "version": version.version,
                "description": version.description,
            }
            for name, version in self._registry.items()
        ]


registry = PromptsRegistry()
registry.add_prompt("loan_eligibility_v1", "prompts.loan_eligibility_v1")
registry.add_prompt("loan_eligibility_v2", "prompts.loan_eligibility_v2")
