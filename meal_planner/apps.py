from django.apps import AppConfig


class MealPlannerConfig(AppConfig):
    name = 'meal_planner'

    def ready(self):
        from . import signals
