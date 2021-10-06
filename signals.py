from django.db.models.signals import post_save
from django.dispatch import receiver

from django.contrib.auth.models import User
from .models import Profile, Recipes, RecipeBox


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, created, **kwargs):
    if not created:
        instance.profile.save()

# @receiver(post_save, sender=Recipes)
# def create_profile(sender, instance, created, **kwargs):
#     if created:
#         RecipeBox.objects.create(recipe_id=instance)
#
# @receiver(post_save, sender=Recipes)
# def save_profile(sender, instance, created, **kwargs):
#     if not created:
#         instance.recipebox.save()
