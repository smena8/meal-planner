import time

import requests
from django.db import IntegrityError
from measurement.measures import Volume
from measurement.utils import guess

import sys
from .models import Recipes, Ingredients, RecipeIngredients

from recipe_scrapers import scrape_me

import environ

# Initialise environment variables
env = environ.Env()

environ.Env.read_env()

# APIS
SPOONACULAR_API_KEY = env('SPOONACULAR_API_KEY')

def recipe_scrape(url):
    # give the url as a string, it can be url from any site listed below
    try:
        scraper = scrape_me(url)
    except:
        scraper = scrape_me(url, wild_mode=True)

    print(scraper.ingredients())


def search_recipe(spoonacular):
    new_qd = {}
    url = f"https://api.spoonacular.com/recipes/{spoonacular}/information"
    new_qd.update({'SPOONACULAR_API_KEY': SPOONACULAR_API_KEY,
                   'includeNutrition': 'true'})
    r = requests.get(url, params=new_qd)
    recipe_data = {}
    if r.status_code == 200:
        json = r.json()
        recipe_data.update({'recipe_name': (json.get('title'))})
        recipe_data.update({'description': (json.get('summary'))})
        recipe_data.update({'minutes': (json.get('readyInMinutes'))})
        recipe_data.update({'servings': (json.get('servings'))})
        extendedIngredients_json = json.get('extendedIngredients')
        recipe_data.update({'ingredients': len(extendedIngredients_json)})
        recipe_data.update({'instructions': (json.get('instructions'))})
        recipe_data.update({'image': (json.get('image'))})
        recipe_data.update({'source_url': (json.get('sourceUrl'))})
        recipe_data.update({'credits_text': (json.get('creditsText'))})
        recipe_data.update({'spoonacular': spoonacular})
        if spoonacular == -1:
            spoonacular = None
        recipe_data.update({'spoonacular': spoonacular})
    try:
        recipes = Recipes(**recipe_data)
        recipes.save()
        ingredients_recipe(extendedIngredients_json, recipe_id=recipes.recipe_id)
    except IntegrityError:
        print(recipes)
    return recipe_data


def extract_recipe(recipe_url):
    new_qd = {}
    url = f"https://api.spoonacular.com/recipes/extract"
    new_qd.update({'SPOONACULAR_API_KEY': SPOONACULAR_API_KEY,
                   'url': recipe_url})
    r = requests.get(url, params=new_qd)
    recipe_data = {}
    if r.status_code == 200:
        json = r.json()
        recipe_data.update({'recipe_name': (json.get('title'))})
        recipe_data.update({'description': (json.get('summary'))})
        recipe_data.update({'minutes': (json.get('readyInMinutes'))})
        recipe_data.update({'servings': (json.get('servings'))})
        extendedIngredients_json = json.get('extendedIngredients')
        if len(extendedIngredients_json) > 1:
            recipe_data.update({'ingredients': len(extendedIngredients_json)})
        else:
            recipe_scrape(recipe_url)
            # use recipe scraper library
        recipe_data.update({'instructions': (json.get('instructions'))})
        recipe_data.update({'image': (json.get('image'))})
        recipe_data.update({'source_url': recipe_url})
        recipe_data.update({'credits_text': (json.get('creditsText'))})
        spoonacular = json.get('id')
        if spoonacular == -1:
            spoonacular = None
        recipe_data.update({'spoonacular': spoonacular})
        recipes = Recipes(**recipe_data)
        recipes.save()
        try:
            ingredients_recipe(extendedIngredients_json, recipe_id=recipes.recipe_id)
        except IntegrityError:
            print(r)
            print(recipes)
        except UnboundLocalError:
            print(r)
            print(recipes)
    return recipe_data


def ingredients_recipe(extendedIngredients_json, recipe_id):
    for ingredient in extendedIngredients_json:
        ingred_data = {}
        rec_ingred_data = {}
        ingredient_spoonacular = ingredient.get('id')
        try:
            ingredient_instance = Ingredients.objects.get(ingredient_spoonacular=ingredient_spoonacular)
        except:
            ingred_data.update({'ingredient_spoonacular': ingredient_spoonacular})
            ingred_data.update({'ingredient_name': (ingredient.get('name'))})
            ingredient_aisle = (ingredient.get('aisle')).split(';')[0]
            ingred_data.update({'ingredient_aisle': ingredient_aisle})
            ingredients = Ingredients(**ingred_data)
            ingredients.save()
            ingredient_instance = Ingredients.objects.get(ingredient_id=ingredients.ingredient_id)

        recipes_instance = Recipes.objects.get(recipe_id=recipe_id)
        rec_ingred_data.update({'recipe_id': recipes_instance})
        rec_ingred_data.update({'ingredient_id': ingredient_instance})

        amount = ingredient.get('amount')
        unit = ingredient.get('unit')
        rec_ingred_data.update({'size': f"{amount} {unit}"})

        measure_choices = {
            'us_tsp': 'US Teaspoon', 'us_tbsp': 'US Tablespoon', 'us_g': 'US Gallon',
            'us_qt': 'US Quart', 'us_pint': 'US Pint', 'us_cup': 'US Cup',
            'us_oz': 'US Ounce', 'us_oz': 'US Fluid Ounce',
            'l': 'liter', 'l': 'litre', 'imperial_g': 'Imperial Gram',
            'imperial_qt': 'Imperial Quart', 'imperial_pint': 'Imperial Pint',
            'imperial_oz': 'Imperial Ounce', 'imperial_tbsp': 'Imperial Tablespoon',
            'imperial_tsp': 'Imperial Teaspoon', 'ml': 'milliliter',
        }

        for measure in measure_choices:
            unit = str(unit)
            if len(unit) > 1:
                if unit[-1] == 's':
                    unit = unit[:-1]
            elif unit == 'g':
                unit = 'imperial_g'
            if unit.lower() in measure_choices[measure].lower():
                unit = guess(amount, measure_choices[measure], measures=[Volume])
                rec_ingred_data.update({'measurement': unit})
            elif unit.lower() in measure.lower():
                unit = guess(amount, measure, measures=[Volume])
                rec_ingred_data.update({'measurement': unit})

        rec_ingredients = RecipeIngredients(**rec_ingred_data)

        try:
            rec_ingredients.save()
        except IntegrityError:
            print(ingredient)
            print(ingred_data)
            print(rec_ingred_data)
            print(Ingredients)
            print(RecipeIngredients)


def convert_to_float(frac_str):
    try:
        return float(frac_str)
    except ValueError:
        num, denom = frac_str.split('/')
        try:
            leading, num = num.split(' ')
            whole = float(leading)
        except ValueError:
            whole = 0
        frac = float(num) / float(denom)
        return whole - frac if whole < 0 else whole + frac
