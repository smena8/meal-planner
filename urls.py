from django.urls import path
from .views import (RecipeBoxListView, RecipeBoxDetailView,
                    ShoppingListView, ShoppingDetailView,
                    MealPlanRedirectView, MealPlanCalendarView,
                    MealPlanCreateView, AddRecipeFormView)
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('meal-plan/', MealPlanRedirectView.as_view(), name='meal-plan'),
    path('meal-plan/<int:year>/<int:month>/<int:day>/', MealPlanCalendarView.as_view(), name='meal-plan-week'),
    path('meal-plan/<int:year>/<int:month>/<int:day>/add/', MealPlanCreateView.as_view(), name='meal-plan-add'),
    path('search-recipes/', views.search_recipes, name='search-recipes'),
    path('recipe-box/', RecipeBoxListView.as_view(), name='recipe-box'),
    path('recipe-box/<int:pk>/', RecipeBoxDetailView.as_view(), name='recipe-box-detail'),
    path('shopping-lists/', ShoppingListView.as_view(), name='shopping-lists'),
    path('shopping-lists/<uuid:uuid>/', ShoppingDetailView.as_view(), name='shopping-lists-detail'),
    path('about-us/', views.aboutus, name='about-us'),
    path('contact/', views.contact, name='contact'),
    path('privacy-policy/', views.privacypolicy, name='privacy-policy'),
    path('login/', auth_views.LoginView.as_view(template_name='meal_planner/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='meal_planner/logout.html'), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('recipe-box/add-recipes-links/', views.add_recipes_links, name='add-recipes-links'),
    path('recipe-box/add-recipes-personal/', AddRecipeFormView.as_view(), name='add-recipes-personal'),
]
