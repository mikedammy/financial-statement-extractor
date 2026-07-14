from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew 
from config.llm import groq_llama, cerebras_llama
from pathlib import Path 
from pydantic import BaseModel, Field
from typing import List, Optional

import time
import random
from functions.log_adder import add_log

def rate_limit_cooldown_callback(task_output):
    """Enforces a strict cooling-off period between consecutive extraction sub-tasks.
    
    This callback acts as a traffic throttle to systematically protect downstream 
    API providers against aggressive burst requests or cascading 429 errors.

    Args:
        task_output (TaskOutput): The structured output data returned by a completed task stage.
    """
    sleep_time = random.uniform(8.0, 12.0)
    add_log(f"Task completed. Triggering anti-backpressure pause for {sleep_time:.2f} seconds to protect API quotas.", level='info', source='STATEMENT_EXTRACTION')
    time.sleep(sleep_time)

CURRENT_DIR = Path(__file__).parent


class FinancialRow(BaseModel):
    """A granular data model outlining a singular structured line item inside a ledger sheet."""
    label: str = Field(description="The financial account line item description (e.g., 'Revenue', 'Cash and Cash Equivalents')")
    level: int = Field(description="Hierarchy/indentation depth relative to parent category. Main titles are 0, sub-accounts are 1, deep sub-items are 2.")
    values: List[str] = Field(description="Array of strings capturing financial values corresponding to each item in the statement column header list sequentially.")


class SingleStatement(BaseModel):
    """A full financial data sheet mapping an array of structured account ledger rows."""
    statement_name: str = Field(description="The unique display sheet name (e.g., 'Balance Sheet', 'Income Statement')")
    columns: List[str] = Field(description="Column structural list representing years or entities in exact order (e.g., ['Group 2023', 'Group 2022'])")
    rows: List[FinancialRow] = Field(description="Ordered array of extracted financial lines following the document physical top-to-bottom layout hierarchy.")


class StatementExtractionOutput(BaseModel):
    """Consolidated blueprint schema serving as the final output for four-task extraction sets."""
    statement_name: str = Field(description="Normalized target verification identifier matching the isolated accounting table context classification.")
    columns: List[str] = Field(description="Clean, non-empty header layout array mapping time scopes or functional segmentation markers.")
    rows: List[FinancialRow] = Field(description="Structured collection of data fields cleanly parsed from the visual data grids.")


@CrewBase
class StatementExtractionCrew:
    """A structured agentic workspace containing rules, target metrics, and tasks to parse 
    unstructured multi-column text records into excel-ready layouts.
    """

    agents_config = str(CURRENT_DIR / 'config/agents.yaml')
    tasks_config = str(CURRENT_DIR / 'config/tasks.yaml')

    @agent
    def statement_extraction_agent(self) -> Agent:
        """Assembles a high-precision table parser runtime module.

        Returns:
            Agent: Fully provisioned tabular scanning entity linked to the core model endpoint.
        """
        add_log("Constructing agent profile context for layout-aware data string conversions.", level='debug', source='STATEMENT_EXTRACTION')
        return Agent(
            config=self.agents_config['statement_extraction_agent'],
            verbose=True,
            llm=cerebras_llama,
            max_iter=2,
            max_retries=2  # Reinforces schema recovery under structural extraction pressure
        )

    @task
    def extract_balance_sheet(self) -> Task:
        """Configures individual targets to extract Statement of Financial Position assets.

        Returns:
            Task: Balance sheet structural data conversion task object description.
        """
        return Task(
            config=self.tasks_config['extract_balance_sheet_task'],
            output_pydantic=SingleStatement,
            agent=self.statement_extraction_agent(),
            callback=rate_limit_cooldown_callback
        )

    @task
    def extract_income_statement(self) -> Task:
        """Configures individual targets to extract Statement of Comprehensive Income line items.

        Returns:
            Task: Profit & Loss structural data conversion task object description.
        """
        return Task(
            config=self.tasks_config['extract_income_statement_task'],
            output_pydantic=SingleStatement,
            agent=self.statement_extraction_agent(),
            callback=rate_limit_cooldown_callback
        )

    @task
    def extract_cash_flow(self) -> Task:
        """Configures individual targets to extract operating, investing, and financing liquid movements.

        Returns:
            Task: Cash flow structural data conversion task object description.
        """
        return Task(
            config=self.tasks_config['extract_cash_flow_task'],
            output_pydantic=SingleStatement,
            agent=self.statement_extraction_agent(),
            callback=rate_limit_cooldown_callback
        )

    @task
    def extract_equity(self) -> Task:
        """Configures individual targets to extract retained earnings and share distributions.

        Returns:
            Task: Shareholders' equity structural data conversion task object description.
        """
        return Task(
            config=self.tasks_config['extract_equity_task'],
            output_pydantic=SingleStatement,
            agent=self.statement_extraction_agent(),
            callback=rate_limit_cooldown_callback
        )

    @crew
    def crew(self) -> Crew:
        """Combines structural configurations to execute sequential table extractions.

        Returns:
            Crew: Production multi-agent pipeline ready for processing tasks.
        """
        add_log("Synthesizing extraction steps into sequential processing thread loops.", level='info', source='STATEMENT_EXTRACTION')
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
