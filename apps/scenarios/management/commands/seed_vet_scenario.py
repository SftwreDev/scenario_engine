from django.core.management.base import BaseCommand
from django.db import transaction

from apps.scenarios.models import Scenario, LearningObjective


DUCHESS_OBJECTIVES = [
    {
        "label": "gather_relevant_history",
        "description": (
            "Ask about feeding, water intake, changes to pasture or diet, and the timeline of symptoms."
        ),
        "order": 1,
    },
    {
        "label": "systematic_assessment",
        "description": (
            "Inquire about specific clinical signs such as temperature, gait, manure consistency, and respiratory rate."
        ),
        "order": 2,
    },
    {
        "label": "environmental_factors",
        "description": (
            "Explore potential environmental causes: pasture type, toxic plants, recent weather, or exposure to other sick animals."
        ),
        "order": 3,
    },
    {
        "label": "identify_differentials",
        "description": (
            "Propose at least two plausible differential diagnoses based on gathered information."
        ),
        "order": 4,
    },
    {
        "label": "treatment_plan",
        "description": (
            "Suggest an appropriate treatment or management plan with reasoning, including immediate actions and follow-up."
        ),
        "order": 5,
    },
]


class Command(BaseCommand):
    help = "Seeds the 'Duchess at Armidale' veterinary scenario with five learning objectives."

    @transaction.atomic
    def handle(self, *args, **options):
        scenario, created = Scenario.objects.get_or_create(
            title="Duchess at Armidale",
            defaults={
                "description": (
                    "A veterinary science student is called to a remote property. Dave, a farmer, is worried about his "
                    "prize Hereford, Duchess, who is off her feed and lethargic."
                ),
                "persona": (
                    "You are Dave, a 55-year-old cattle farmer from rural NSW. You speak in plain language, get anxious "
                    "if the student seems unsure, and occasionally throw in irrelevant details about your other cattle or the weather."
                ),
                "setting": (
                    "A remote property outside Armidale, NSW. It's a cool autumn morning. You called the university clinic because Duchess isn't right."
                ),
                "context": (
                    "Duchess has been off her feed since yesterday afternoon, seems a bit listless, and is hanging back from the mob. "
                    "You noticed her manure looked a bit loose last night. Water troughs are working. Recent rain after a dry spell."
                ),
                "conversation_instructions": (
                    "Be helpful but not medically precise. Describe what you see in plain language. Get mildly anxious if the student seems unsure. "
                    "Occasionally add small irrelevant details. Do not volunteer critical clinical information unless asked."
                ),
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created scenario: {scenario.title}"))
        else:
            self.stdout.write(
                self.style.WARNING(f"Scenario already exists: {scenario.title}")
            )

        # Seed learning objectives (idempotent by label within scenario)
        created_count = 0
        for obj_data in DUCHESS_OBJECTIVES:
            lo, lo_created = LearningObjective.objects.get_or_create(
                scenario=scenario,
                label=obj_data["label"],
                defaults={
                    "description": obj_data["description"],
                    "order": obj_data.get("order"),
                    "is_sequential": False,
                },
            )
            created_count += 1 if lo_created else 0

        if created_count:
            self.stdout.write(
                self.style.SUCCESS(f"Added {created_count} new learning objectives.")
            )
        else:
            self.stdout.write("All learning objectives already present.")
