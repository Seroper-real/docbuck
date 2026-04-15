from abc import ABC, abstractmethod


class Chain(ABC):
    name: str
    description: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "name") or not hasattr(cls, "description"):
            raise TypeError(f"{cls.__name__} must define 'name' and 'description'")

    @property
    def llm_line(self) -> str:
        return f"- **{self.name}**: {self.description}."

    def query(self, prompt):
        ...