from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.scenarios.services import scenario_create, learning_objective_create
from apps.session.models import Session, SessionObjectiveProgress
from apps.session.services import session_create

User = get_user_model()


class SessionModelTests(TestCase):
    def setUp(self):
        self.scenario = scenario_create(
            title="Test Scenario",
            persona="Persona",
            setting="Setting",
            context="Context",
        )
        self.user = User.objects.create_user(username="testuser", password="password")

    def test_session_creation(self):
        session = Session.objects.create(scenario=self.scenario, user=self.user)
        self.assertEqual(str(session), "Test Scenario")
        self.assertTrue(session.is_active)
        self.assertIsNone(session.summarised_up_to_sequence)
        self.assertEqual(session.context_summary, "")

    def test_session_objective_progress_creation(self):
        session = Session.objects.create(scenario=self.scenario)
        objective = learning_objective_create(
            scenario=self.scenario,
            label="Test Objective",
            description="Objective description",
        )
        progress = SessionObjectiveProgress.objects.create(
            session=session,
            objective=objective,
            is_met=True,
            justification="Did a great job",
        )
        self.assertTrue(progress.is_met)
        self.assertEqual(str(progress), f"Session {session.id} - Test Objective: Met")
        self.assertEqual(progress.justification, "Did a great job")


class SessionServiceTests(TestCase):
    def setUp(self):
        self.scenario = scenario_create(
            title="Test Scenario",
            persona="Persona",
            setting="Setting",
            context="Context",
        )
        self.user = User.objects.create_user(username="testuser", password="password")

    def test_session_create_service(self):
        session = session_create(scenario=self.scenario, user=self.user)
        self.assertIsInstance(session, Session)
        self.assertEqual(session.scenario, self.scenario)
        self.assertEqual(session.user, self.user)
        self.assertTrue(session.is_active)

    def test_session_create_service_no_user(self):
        session = session_create(scenario=self.scenario)
        self.assertIsNone(session.user)
        self.assertEqual(session.scenario, self.scenario)
