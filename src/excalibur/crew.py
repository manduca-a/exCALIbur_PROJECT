from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from dotenv import load_dotenv                            # ← ADD this whole line
import os                                                 # ← ADD this whole line

from .tools.custom_tool import AmbulanceEtaTool, AssignAmbulanceTool, HospitalLocatorTool

load_dotenv()                                             # ← ADD

# Explicit Groq LLM — needed for Windows machines where           ← ADD this whole block
# CrewAI's default LLM detection fails with WinError 10061        ← ADD
groq_llm = LLM(                                                   # ← ADD
    model="groq/llama-3.3-70b-versatile",                         # ← ADD
    api_key=os.getenv("GROQ_API_KEY"),                            # ← ADD
    base_url="https://api.groq.com/openai/v1",                    # ← ADD
)                                                                 # ← ADD

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
            llm=groq_llm,                                # ← ADD this line
            verbose=True
        )
    
    @agent
    def ambulance_dispatcher(self) -> Agent:
        return Agent(
            config=self.agents_config['ambulance_dispatcher'],
            tools=[AmbulanceEtaTool(), AssignAmbulanceTool()],
            llm=groq_llm,                                # ← ADD this line
            verbose=True
        )
    @agent
    def hospital_locator(self) -> Agent:
        return Agent(
            config=self.agents_config['hospital_locator'],
            tools=[HospitalLocatorTool()],
            llm=groq_llm,
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task


    # TODO: add am agent that, given the patient's symptoms, looks for the nearest hospital with free beds and the right specialization

    @agent
    def rehabilitation_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['rehabilitation_specialist'],
            verbose=True
        )

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
    
    @task
    def hospital_locator_task(self) -> Task:
        return Task(
            config=self.tasks_config['hospital_locator_task'],
        )

    # TODO: add a task for the hospital locator agent
    
    @task
    def rehabilitation_task(self) -> Task:
        return Task(
            config=self.tasks_config['rehabilitation_task'],
        )

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
