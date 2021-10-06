from django.contrib import admin
from .models import (Profile, Recipes, RecipeBox,
                     Ingredients, RecipeIngredients,
                     ShoppingList, ShoppingListItems,
                    MealPlanCalendar)

# Register your models here.
admin.site.register(Profile)
admin.site.register(Recipes)
admin.site.register(RecipeBox)
admin.site.register(Ingredients)
admin.site.register(RecipeIngredients)
admin.site.register(ShoppingList)
admin.site.register(ShoppingListItems)
admin.site.register(MealPlanCalendar)
