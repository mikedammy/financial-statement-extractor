from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task
from config.llm import groq_llama
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

CURRENT_DIR = Path(__file__).parent

class ProfitabilityMetrics(BaseModel):
    """Data frame containing core profit margin percentages and capital return calculations."""
    gross_margin: Optional[float] = Field(None, description="Gross Margin ratio")
    ebitda_margin: Optional[float] = Field(None, description="EBITDA Margin ratio")
    operating_margin: Optional[float] = Field(None, description="Operating Margin ratio")
    pre_tax_margin: Optional[float] = Field(None, description="Pre-tax Margin ratio")
    net_profit_margin: Optional[float] = Field(None, description="Net Profit Margin ratio")
    return_on_assets: Optional[float] = Field(None, description="Return on Assets (ROA)")
    return_on_equity: Optional[float] = Field(None, description="Return on Equity (ROE)")
    return_on_capital_employed: Optional[float] = Field(None, description="Return on Capital Employed (ROCE)")
    effective_tax_rate: Optional[float] = Field(None, description="Effective Tax Rate")

class LiquidityMetrics(BaseModel):
    """Data frame tracking immediate cash conversion capabilities and operational funding assets."""
    current_ratio: Optional[float] = Field(None, description="Current Ratio")
    quick_ratio: Optional[float] = Field(None, description="Quick Ratio")
    cash_ratio: Optional[float] = Field(None, description="Cash Ratio")
    net_working_capital: Optional[float] = Field(None, description="Net Working Capital value")

class SolvencyMetrics(BaseModel):
    """Data schema structural records holding systemic leverage multipliers and asset velocity times."""
    debt_to_equity: Optional[float] = Field(None, description="Debt to Equity ratio")
    debt_ratio: Optional[float] = Field(None, description="Debt Ratio")
    equity_multiplier: Optional[float] = Field(None, description="Equity Multiplier")
    interest_coverage: Optional[float] = Field(None, description="Interest Coverage ratio")
    asset_turnover: Optional[float] = Field(None, description="Asset Turnover ratio")
    days_sales_outstanding: Optional[float] = Field(None, description="Days Sales Outstanding (DSO)")
    days_inventory_outstanding: Optional[float] = Field(None, description="Days Inventory Outstanding (DIO)")
    days_payable_outstanding: Optional[float] = Field(None, description="Days Payable Outstanding (DPO)")
    cash_conversion_cycle: Optional[float] = Field(None, description="Cash Conversion Cycle")

class CashFlowQualityMetrics(BaseModel):
    """Data frame containing free reinvestment balances and operational metrics indicators."""
    operating_cash_flow: Optional[float] = Field(None, description="Operating Cash Flow value")
    free_cash_flow: Optional[float] = Field(None, description="Free Cash Flow value")
    quality_of_earnings: Optional[float] = Field(None, description="Quality of Earnings ratio")
    capital_reinvestment_ratio: Optional[float] = Field(None, description="Capital Reinvestment ratio")

class FinancialHighlightsOutput(BaseModel):
    """Consolidated master tracking layout mapping across all sub-metric evaluation layers."""
    profitability_and_returns: ProfitabilityMetrics = Field(..., description="Calculated profitability metrics")
    liquidity_metrics: LiquidityMetrics = Field(..., description="Calculated liquidity metrics")
    solvency_and_leverage: SolvencyMetrics = Field(..., description="Calculated solvency and leverage metrics")
    cash_flow_quality: CashFlowQualityMetrics = Field(..., description="Calculated cash flow quality metrics")


@CrewBase
class FinancialHighlightsCrew:
    """An analytical multi-agent runtime layout configuration designed to scan standard statements 
    and evaluate core operational metrics records.
    """

    agents_config = str(CURRENT_DIR / "config/agents.yaml")
    tasks_config = str(CURRENT_DIR / "config/tasks.yaml")

    @agent
    def financial_highlights_agent(self) -> Agent:
        """Assembles the specialized execution context tracking financial metrics calculations.

        Returns:
            Agent: Fully structured analytical computational runtime profile container.
        """
        return Agent(
            config=self.agents_config["financial_highlights_agent"],
            verbose=True,
            llm=groq_llama,
            max_retries=2  # Expanded execution retry margin for resiliency
        )
        
    @task
    def financial_highlights_task(self) -> Task:
        """Compiles raw statements text logs into structured categorical evaluation formulas.

        Returns:
            Task: Target directive pairing tracking structured Pydantic return layout properties.
        """
        return Task(
            config=self.tasks_config["financial_highlights_task"],
            agent=self.financial_highlights_agent(),
            output_pydantic=FinancialHighlightsOutput
        )
    
    def crew(self) -> Crew:
        """Organizes configured tasks elements into a synchronized production environment.

        Returns:
            Crew: Production multi-agent sequential pipeline execution orchestrator.
        """
        return Crew(
            agents=[self.financial_highlights_agent()],
            tasks=[self.financial_highlights_task()],
            process=Process.sequential,
            verbose=True,
            rpm_limit=10
        )
