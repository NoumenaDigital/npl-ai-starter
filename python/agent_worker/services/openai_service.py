import logging
import os

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr, BaseModel, Field

from agent_worker.config import OpenAIConfig

logger = logging.getLogger(__name__)


class OpenAIError(Exception):
    """Base class for OpenAI service errors."""
    pass


class TicketParse(BaseModel):
    """Parsed ticket structure."""
    title: str = Field(description="A concise title for the ticket")
    contents: str = Field(description="Detailed ticket contents and implementation notes")


class OpenAIService:
    def __init__(self, config: OpenAIConfig):
        logger.debug(f"Initializing OpenAI service with deployment: {config.deployment_name}")

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if not endpoint or not api_key:
            logger.error("Missing Azure OpenAI credentials")
            raise OpenAIError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

        logger.debug(f"Using Azure OpenAI endpoint: {endpoint}")

        try:
            self.llm = AzureChatOpenAI(
                azure_deployment=config.deployment_name,
                temperature=config.temperature,
                max_tokens=None,
                max_retries=config.max_retries,
                api_version=config.api_version,
                azure_endpoint=endpoint,
                api_key=SecretStr(api_key)
            )
            logger.info("OpenAI service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {e}")
            raise OpenAIError(f"Failed to initialize OpenAI service: {str(e)}") from e

    def parse_requirements_to_ticket(self, requirements: str) -> TicketParse:
        """
        Parse business requirements into a structured ticket format.
        
        Args:
            requirements (str): The business requirements text
            
        Returns:
            TicketParse: A structured ticket with title and contents
            
        Raises:
            OpenAIError: If there's an error parsing the requirements
        """
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

            # Create a chain that will:
            # 1. Take the input and pass it through
            # 2. Format the prompt with the input and format instructions
            # 3. Send to LLM
            # 4. Parse the response into a TicketParse object
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
            raise OpenAIError(f"Failed to parse requirements: {str(e)}") from e
