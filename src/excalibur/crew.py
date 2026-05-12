from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from .tools.custom_tool import AmbulanceEtaTool

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class Excalibur():
    """Excalibur crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['analyzer'],
            verbose=True
        )
    
    @agent
    def ambulance_dispatcher(self) -> Agent:
        return Agent(
            config=self.agents_config['ambulance_dispatcher'],
            tools=[AmbulanceEtaTool()],
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task

    # TODO: add an agent that act like an actor, so from given addresses and symptoms, it "call" the hospital to ask for help

    # TODO: add am agent that, given the patient's symptoms, looks for the nearest hospital with free beds and the right specialization

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'], # type: ignore[index]
        )
    
    @task
    def dispatch_task(self) -> Task:
        return Task(
            config=self.tasks_config['dispatch_task'],
        )

    # TODO: add a task for the actor agent

    # TODO: add a task for the hospital locator agent

    @crew
    def crew(self) -> Crew:
        """Creates the Excalibur crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
