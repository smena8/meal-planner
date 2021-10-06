import time
import uuid
from datetime import datetime, date, timedelta

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from PIL import Image

from django.utils import timezone
from django_measurement.models import MeasurementField
from measurement.measures import Volume, Energy

from cloudinary.models import CloudinaryField


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = CloudinaryField('image', transformation={'width': '300', 'height': '300', 'crop':'fill'}, format="jpg", use_filename='true')
    tnc = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} Profile"


# @receiver(post_save, sender=User)
# def create_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)
#         print('Profile created!')
#
# # post_save.connect(create_profile, sender=User)
#
# @receiver(post_save, sender=User)
# def save_profile(sender, instance, created, **kwargs):
#     if not created:
#         instance.profile.save()
#         print('Profile updated!')
#
# # post_save.connect(save_profile, sender=User)

class Recipes(models.Model):
    recipe_id = models.AutoField(primary_key=True, editable=False, unique=True)
    recipe_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    minutes = models.IntegerField(default=60, null=True, blank=True)
    servings = models.CharField(max_length=50, null=True, blank=True)
    ingredients = models.CharField(max_length=200)
    instructions = models.TextField(blank=True, null=True)
    image = models.URLField(max_length=300)
    source_url = models.URLField(max_length=200, null=True, blank=True)
    credits_text = models.CharField(max_length=200, null=True, blank=True)
    date_added = models.DateTimeField(default=timezone.now)
    spoonacular = models.IntegerField(default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.recipe_name} -- {self.credits_text}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['recipe_name', 'source_url'], name='recipes_constraint')
        ]

    def get_absolute_url(self):
        return reverse('recipe-box-detail', kwargs={'pk': self.pk})


class RecipeBox(models.Model):
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    recipe_id = models.ForeignKey(Recipes, on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)
    favorite = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.recipe_id.recipe_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe_id'], name='recipe_box_constraint')
        ]
        ordering = ['-date_added']


class Ingredients(models.Model):
    ingredient_id = models.AutoField(primary_key=True)
    ingredient_spoonacular = models.IntegerField(unique=True, null=True, blank=True)
    ingredient_name = models.CharField(max_length=200)
    ingredient_aisle = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.ingredient_name} -- {self.ingredient_id}"

    class Meta:
        ordering = ['ingredient_aisle']


class RecipeIngredients(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    recipe_id = models.ForeignKey(Recipes, on_delete=models.CASCADE)
    ingredient_id = models.ForeignKey(Ingredients, on_delete=models.CASCADE)
    MEASURE_CHOICES = [
        ('us_tsp', 'US Teaspoon'),
        ('us_tbsp', 'US Tablespoon'),
        ('us_g', 'US Gallon'), ('us_qt', 'US Quart'), ('us_pint', 'US Pint'),
        ('us_cup', 'US Cup'), ('us_oz', 'US Ounce'), ('us_oz', 'US Fluid Ounce'),
        ('l', 'liter'), ('l', 'litre'), ('imperial_g', 'Imperial Gram'),
        ('imperial_qt', 'Imperial Quart'), ('imperial_pint', 'Imperial Pint'),
        ('imperial_oz', 'Imperial Ounce'), ('imperial_tbsp', 'Imperial Tablespoon'),
        ('imperial_tsp', 'Imperial Teaspoon'), ('ml', 'milliliter'),
    ]
    measurement = MeasurementField(measurement=Volume, null=True, blank=True, unit_choices=MEASURE_CHOICES)
    size = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f"{self.ingredient_id} -- {self.measurement} -- {self.size}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['recipe_id', 'ingredient_id', 'measurement', 'size'],
                                    name='recipe_ing_constraint')
        ]


class Nutrients(models.Model):
    nutrient_id = models.IntegerField(primary_key=True)
    nutrient_name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.nutrient_name}"


class RecipeNutrients(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    recipe_id = models.ForeignKey(Recipes, on_delete=models.CASCADE)
    nutrient_id = models.ForeignKey(Nutrients, on_delete=models.CASCADE)
    nutrient_cal = MeasurementField(measurement=Energy, default=0)
    nutrient_qty = MeasurementField(measurement=Volume, default=0)


class ShoppingList(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    list_title = models.CharField(max_length=200, unique=True, default=f"Shopping List {datetime.now()}")

    def __str__(self):
        return f"{self.list_title} -- {self.user.username}"


class ShoppingListItems(models.Model):
    list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE)
    recipe_ing_id = models.ForeignKey(RecipeIngredients, on_delete=models.CASCADE)
    obtained = models.BooleanField(default=False)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.list.list_title} -- {self.list.user}"

    class Meta:
        ordering = ['obtained']


class MealPlanCalendar(models.Model):
    recipebox = models.ForeignKey(RecipeBox, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    start_week = models.DateField()
    end_week = models.DateField()
    leftovers = models.BooleanField(default=False)
    BREAKFAST = 'BR'
    LUNCH = 'LU'
    DINNER = 'DN'
    DESSERT = 'DS'
    SNACK = 'SN'
    DRINKS = 'DK'
    MEAL_CHOICES = [
        (BREAKFAST, 'Breakfast'),
        (LUNCH, 'Lunch'),
        (DINNER, 'Dinner'),
        (DESSERT, 'Dessert'),
        (SNACK, 'Snack'),
        (DRINKS, 'Drinks'),
    ]
    course = models.CharField(
        max_length=10,
        choices=MEAL_CHOICES,
    )

    def __str__(self):
        return f"{self.start_date} -- {self.course} -- {self.recipebox.user}"

    def save(self, *args, **kwargs):
        year = int(self.start_date.strftime("%Y").strip("0"))
        month = int(self.start_date.strftime("%m").strip("0"))
        day = int(self.start_date.strftime("%d").strip("0"))
        week = datetime(year, month, day).isocalendar()[1]
        start_week = date.fromisocalendar(year=year, week=week, day=1)
        end_week = start_week + timedelta(days=6)
        self.start_week = start_week
        self.end_week = end_week
        super(MealPlanCalendar, self).save(*args, **kwargs)
