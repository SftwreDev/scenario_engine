"""Prompt construction utilities for scenario conversations.

Builds concise system prompts that encode persona, setting, context, and
objective information for the LLM. Docstrings use a neutral tone.
"""

from apps.scenarios.models import Scenario


class PromptBuilder:
    """Build system prompts for role-play style scenarios.

    Produces prompts that keep the model in character and surface the
    scenario details required for consistent behaviour.
    """

    RESPONSE_FORMAT_INSTRUCTION = """
        ## Response Format (CRITICAL — always follow this exactly)
        
        You must ALWAYS respond with valid JSON in this exact structure. No exceptions.
        ```json
        {
          "character_response": "<your in-character dialogue as the persona>",
          "assessment": {
            "objectives_touched": ["<objective_key>", ...],
            "objective_progress": {
              "<objective_key>": {
                "status": "not_started|in_progress|demonstrated",
                "notes": "<brief assessor note on what the learner did re: this objective>"
              }
            },
            "overall_progress": <integer 0-100>,
            "scenario_state": "<short label for current phase, e.g. 'history_gathering'>",
            "assessor_notes": "<your overall read on the learner's performance so far>"
          }
        }
        ```
        
        Rules:
        - character_response must be natural in-character dialogue only. No meta-commentary.
        - objectives_touched lists only objectives the learner's LAST message meaningfully engaged with.
        - objective_progress must include ALL objectives every time, even ones not yet started.
        - overall_progress is your honest cumulative assessment, not just this turn.
        - Never break character in character_response.
        - Never mention the JSON structure or assessment to the learner.
"""

    def build_system_prompt(self, scenario: Scenario) -> str:
        """
        Builds a system prompt for a specific scenario to guide AI simulations in role-playing contexts.

        Parameters:
        scenario (Scenario): The scenario object containing details such as title, persona, description,
        setting, context, and learning objectives.

        Returns:
        str: A formatted string that acts as the system prompt for the simulation.

        Raises:
        None
        """
        objectives_text = self._format_objectives(scenario)
        return f"""# Scenario: {scenario.title}
            
            ## Your Role
            You are playing the character of {scenario.persona}.
            
            ## Character Description
            {scenario.description}
            
            ## Setting
            {scenario.setting}
            
            ## Situation
            {scenario.context}
            
            ## Learning Objectives
            The learner is being assessed against these objectives. Track their progress carefully.
            
            {objectives_text}
            
            ## Staying In Character
            - Never break character or acknowledge you are an AI.
            - Respond as {scenario.persona} would — in plain language, with their personality.
            - If the learner asks something outside your character's knowledge, respond as the character would (uncertain, anxious, honest about what they don't know).
            - You may volunteer small irrelevant details occasionally to simulate a realistic conversation.
            
            {self.RESPONSE_FORMAT_INSTRUCTION}"""

    def _format_objectives(self, scenario: Scenario) -> str:
        """
        Formats learning objectives from a given scenario into a formatted string.

        This method retrieves the learning objectives from the provided scenario, formats each
        objective with its key, title, and description, and compiles them into a structured string
        with each objective clearly delineated.

        Parameters:
            scenario (Scenario): The scenario object from which learning objectives are retrieved.

        Returns:
            str: A formatted string containing all learning objectives from the provided scenario.
        """
        objectives = scenario.learning_objectives.select_related().all()

        lines = []
        for obj in objectives:
            lines.append(f"### Objective: {obj.key}")
            lines.append(f"**Label:** {obj.label}")
            lines.append(f"**Description:** {obj.description}")
            lines.append("")

        return "\n".join(lines)
