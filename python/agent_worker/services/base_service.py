import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base class for LLM service errors."""
    pass


class TicketParse(BaseModel):
    """Parsed ticket structure."""
    title: str = Field(description="A concise title for the ticket")
    contents: str = Field(description="Detailed ticket contents and implementation notes")


class BaseLLMService(ABC):
    """Base class for LLM services."""
    
    def __init__(self, config: Any):
        """Initialize the service with configuration."""
        logger.debug(f"Initializing {self.__class__.__name__}")
        self.config = config
        self.llm: Optional[BaseChatModel] = None  # Initialize the llm attribute
        self._initialize_llm()
        
    @abstractmethod
    def _initialize_llm(self):
        """Initialize the LLM client."""
        pass

    def parse_requirements_to_ticket(self, requirements: str) -> TicketParse:
        """Parse business requirements into a structured ticket format."""
        try:
            parser = PydanticOutputParser(pydantic_object=TicketParse)
            prompt = ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(
                    """Convert the following business requirements into a structured engineering ticket.
                    The ticket should have a clear title and detailed implementation notes.
                    
                    Requirements:
                    {input}
                    
                    {format_instructions}
                    """
                )
            ])

            chain = (
                RunnablePassthrough()
                | prompt.partial(format_instructions=parser.get_format_instructions())
                | self.llm
                | parser
            )

            logger.debug(f"Processing requirements: {requirements}")
            result = chain.invoke(requirements)
            logger.debug(f"Generated ticket: {result}")

            return result
        except Exception as e:
            logger.error(f"Failed to parse requirements: {e}")
            raise LLMServiceError(f"Failed to parse requirements: {str(e)}") from e 