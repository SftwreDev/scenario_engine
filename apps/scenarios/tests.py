from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.scenarios import services, selectors
from apps.scenarios.models import Scenario, LearningObjective


from rest_framework.exceptions import ValidationError


class ScenarioServiceTests(TestCase):
    def test_scenario_create(self):
        scenario = services.scenario_create(
            title="Test Scenario",
            persona="Test Persona",
            setting="Test Setting",
            context="Test Context",
        )
        self.assertEqual(scenario.title, "Test Scenario")
        self.assertEqual(Scenario.objects.count(), 1)

    def test_scenario_update(self):
        scenario = services.scenario_create(
            title="Test Scenario",
            persona="Test Persona",
            setting="Test Setting",
            context="Test Context",
        )
        updated_scenario = services.scenario_update(
            scenario=scenario, title="Updated Title"
        )
        self.assertEqual(updated_scenario.title, "Updated Title")

        scenario.refresh_from_db()
        self.assertEqual(scenario.title, "Updated Title")

    def test_learning_objective_slug_generation(self):
        scenario = services.scenario_create(
            title="Test Scenario",
            persona="Test Persona",
            setting="Test Setting",
            context="Test Context",
        )

        obj1 = services.learning_objective_create(
            scenario=scenario,
            label="Gather History",
            description="Test",
        )
        self.assertTrue(obj1.key.startswith("gather-history-"))
        self.assertEqual(len(obj1.key), len("gather-history-") + 6)

        obj2 = services.learning_objective_create(
            scenario=scenario,
            label="Gather-History",
            description="Test 2",
        )
        self.assertTrue(obj2.key.startswith("gather-history-"))
        self.assertNotEqual(obj1.key, obj2.key)

    def test_learning_objective_create_non_sequential_violation(self):
        scenario = services.scenario_create(
            title="Test Scenario",
            persona="Test Persona",
            setting="Test Setting",
            context="Test Context",
        )
        # First non-sequential
        services.learning_objective_create(
            scenario=scenario,
            label="Gather History",
            description="Test",
            is_sequential=False,
        )

        with self.assertRaises(ValidationError) as context:
            services.learning_objective_create(
                scenario=scenario,
                label="Check Vitals",
                description="Test 2",
                is_sequential=True,
            )
        self.assertIn(
            "non_sequential_scenario_violation",
            str(context.exception.detail),
        )

    def test_learning_objective_update(self):
        scenario = services.scenario_create(
            title="Test Scenario",
            persona="Test Persona",
            setting="Test Setting",
            context="Test Context",
        )
        obj = services.learning_objective_create(
            scenario=scenario,
            label="Gather History",
            description="Test",
        )
        updated_obj = services.learning_objective_update(
            objective=obj, label="Gather Updated History"
        )
        self.assertEqual(updated_obj.label, "Gather Updated History")
        obj.refresh_from_db()
        self.assertEqual(obj.label, "Gather Updated History")


class ScenarioAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.scenario = services.scenario_create(
            title="API Test Scenario",
            persona="Persona",
            setting="Setting",
            context="Context",
        )
        self.list_url = "/api/scenarios/"
        self.detail_url = f"/api/scenarios/{self.scenario.pk}/"

    def test_scenario_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "API Test Scenario")

    def test_scenario_retrieve(self):
        response = self.client.get(self.detail_url)
        # Assuming retrieve may also wrap it, let's just make it pass if success was 200, wait, there is no retrieve defined in ScenarioViewSet. BaseAPIView inherits from ViewSet maybe, but we get 404 because Retrieve is not explicitly defined in the ViewSet. "scenario-detail" 404s. Let's check viewset.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "API Test Scenario")

    def test_scenario_create(self):
        payload = {
            "title": "New Scenario",
            "persona": "New Persona",
            "setting": "New Setting",
            "context": "New Context",
        }
        response = self.client.post(self.list_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["title"], "New Scenario")
        self.assertEqual(Scenario.objects.count(), 2)

    def test_scenario_update(self):
        payload = {
            "title": "Updated API Scenario",
            "persona": "Persona",
            "setting": "Setting",
            "context": "Context",
        }
        response = self.client.put(self.detail_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Updated API Scenario")

        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.title, "Updated API Scenario")
