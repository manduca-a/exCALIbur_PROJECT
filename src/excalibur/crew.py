from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from .tools.custom_tool import (
    AmbulanceEtaTool,
    AssignAmbulanceTool,
    HospitalLocatorTool,
    ReserveHospitalBedTool,
)
from .llm_config import groq_llm


@CrewBase
class Excalibur():
    """Excalibur crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def supervisor(self) -> Agent:
        return Agent(
            config=self.agents_config['supervisor'],
            llm=groq_llm,
            verbose=True
        )

    @agent
    def analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['analyzer'],
            llm=groq_llm,
            verbose=True
        )

    @agent
    def ambulance_dispatcher(self) -> Agent:
        return Agent(
            config=self.agents_config['ambulance_dispatcher'],
            tools=[AmbulanceEtaTool(), AssignAmbulanceTool()],
            llm=groq_llm,
            verbose=True
        )

    @agent
    def hospital_locator(self) -> Agent:
        return Agent(
            config=self.agents_config['hospital_locator'],
            tools=[HospitalLocatorTool(), ReserveHospitalBedTool()],
            llm=groq_llm,
            verbose=True
        )

    @agent
    def rehabilitation_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['rehabilitation_specialist'],
            llm=groq_llm,
            verbose=True
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'],
        )

    @task
    def dispatch_task(self) -> Task:
        return Task(
            config=self.tasks_config['dispatch_task'],
            context=[self.analysis_task()],
        )

    @task
    def hospital_locator_task(self) -> Task:
        return Task(
            config=self.tasks_config['hospital_locator_task'],
            context=[self.analysis_task()],
        )

    @task
    def rehabilitation_task(self) -> Task:
        return Task(
            config=self.tasks_config['rehabilitation_task'],
            context=[self.analysis_task(), self.hospital_locator_task(), self.dispatch_task()]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Excalibur crew"""
        manager = self.supervisor()
        workers = [agent for agent in self.agents if agent != manager]
        return Crew(
            agents=workers,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=True,
        )