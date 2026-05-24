from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from .llm_config import big_llm, medium_llm, small_llm


@CrewBase
class SimulatorCrew():
    """Crew responsible for simulating random emergency calls"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = 'config/simulator_agents.yaml'
    tasks_config = 'config/simulator_tasks.yaml'

    @agent
    def emergency_caller_simulator(self) -> Agent:
        return Agent(
            config=self.agents_config['emergency_caller_simulator'],
            llm=small_llm,
            verbose=False
        )

    @task
    def simulation_task(self) -> Task:
        return Task(
            config=self.tasks_config['simulation_task'],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )