import time
from datetime import datetime, date, timedelta

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail, BadHeaderError
from django.db import IntegrityError
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    TemplateView, RedirectView)
from django.views.generic.edit import FormMixin, FormView
from measurement.measures import Volume
from measurement.utils import guess
from recipe_scrapers import scrape_me
from . import spoonacular_api

from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, MealPlanForm, CreateRecipesForm, \
    IngredientsForm, RecipeIngredientsForm, ContactForm
from .models import Recipes, RecipeBox, User, ShoppingList, ShoppingListItems, RecipeIngredients, MealPlanCalendar, \
    Ingredients
from .spoonacular_api import convert_to_float

from cloudinary.forms import cl_init_js_callbacks


def home(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form_data = {
                'first_name': form.cleaned_data.get('firstname'),
                'last_name': form.cleaned_data.get('lastname'),
                'username': form.cleaned_data.get('username'),
                'email': form.cleaned_data.get('email'),
                'password': form.cleaned_data.get('password2')
            }
            new_user = User.objects.create_user(**form_data)
            new_user.save()

            messages.success(request, f"Welcome {form_data['first_name']}! You are now ready to login.")
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'meal_planner/home.html', {'form': form})


@login_required
def search_recipes(request):
    recipebox = RecipeBox.objects.all().filter(user=request.user)

    recipebox_ids_list = []
    for recipe in recipebox:
        recipebox_ids_list.append(recipe.recipe_id.spoonacular)

    context = {}
    url = 'https://api.spoonacular.com/recipes/complexSearch?apiKey=4819eceacc114529844b972ab2da8da8' \
          '&addRecipeInformation=True' \
          '&sort=popularity' \
          '&number=20'
    query = ""
    new_qd = {}

    if request.method == 'POST':
        spoonacular = request.POST['recipe_id']
        if spoonacular:
            recipe_data = spoonacular_api.search_recipe(spoonacular)

            recipe_id = Recipes.objects.all().filter(spoonacular=spoonacular)[0]
            user = User.objects.all().filter(username=request.user)[0]

            try:
                RecipeBox.objects.create(recipe_id=recipe_id, user=user)
                messages.success(request, f"Your recipe box has been updated.")
                context = {'recipe_data': recipe_data}
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
            except IntegrityError:
                messages.error(request, f"This recipe is already in your recipe box.")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        else:
            messages.error(request, f"Sorry, we were unable to add this to your recipe box.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    if request.method == 'GET':
        try:
            query = request.GET['query']
            qd = request.GET
            filtered_list = []
            for key in qd:
                value = request.GET.getlist(key)
                if len(value) >= 1:
                    param_list_string = ",".join(str(w) for w in value)
                    if key != 'query':
                        filtered_list.append((",".join(str(w) for w in value)))
                    value = param_list_string
                new_qd.update({key: value})
            split_filtered_list = (", ".join(str(w.title()) for w in filtered_list)).split(',')
            if split_filtered_list[0] != '':
                context.update({'filtered': split_filtered_list})
        except:
            pass

    r = requests.get(url, params=new_qd)
    if r.status_code == 200:
        json = r.json()
        results = json.get('results')
        context.update({'results': results,
                        'query': query,
                        'recipebox': recipebox_ids_list})
        return render(request, 'meal_planner/search-recipes.html', context)


class RecipeBoxListView(LoginRequiredMixin, ListView):
    model = RecipeBox
    template_name = 'meal_planner/recipe-box.html'
    context_object_name = 'recipes'
    ordering = ['-date_added']
    paginate_by = 10

    def get_queryset(self):
        search_recipe_box = self.request.GET.get('search_recipe_box')
        if search_recipe_box:
            object_list = RecipeBox.objects.filter(user=self.request.user).filter(
                recipe_id_id__recipe_name__icontains=search_recipe_box)
        else:
            object_list = RecipeBox.objects.filter(user=self.request.user)
        list_sort = self.request.GET.get('select_option')
        if list_sort == 'Newest':
            object_list = object_list
        elif list_sort == 'Oldest':
            object_list = object_list.order_by('date_added')
        elif list_sort == 'Favorite':
            object_list = object_list.order_by('-favorite')
        elif list_sort == 'A-Z':
            object_list = object_list.order_by('recipe_id_id__recipe_name')
        elif list_sort == 'Z-A':
            object_list = object_list.order_by('-recipe_id_id__recipe_name')
        return object_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_recipe_box = self.request.GET.get('search_recipe_box')
        if search_recipe_box:
            context['search_query'] = search_recipe_box
        list_sort = self.request.GET.get('select_option')
        if list_sort:
            context['list_sort'] = list_sort
        # context.update(self.extra_context)
        return context

    def post(self, request):
        if request.method == 'POST':
            recipe_id = request.POST.get('recipe_id')
            fav_false_recipe = request.POST.get('fav_false_recipe')
            fav_true_recipe = request.POST.get('fav_true_recipe')
            add_to_meal_plan = request.POST.get('add_to_meal_plan')
            add_to_shopping = request.POST.get('add_to_shopping')
            delete_recipe = request.POST.get('delete_recipe')
            if fav_false_recipe:
                recipe = RecipeBox.objects.filter(user=self.request.user).get(recipe_id=fav_false_recipe)
                recipe.favorite = True
                recipe.save()
            elif fav_true_recipe:
                recipe = RecipeBox.objects.filter(user=self.request.user).get(recipe_id=fav_true_recipe)
                recipe.favorite = False
                recipe.save()
            elif delete_recipe:
                recipe = RecipeBox.objects.filter(user=self.request.user).get(recipe_id=delete_recipe)
                recipe.delete()
        return redirect('recipe-box')


class RecipeBoxDetailView(DetailView):
    model = RecipeBox
    context_object_name = 'recipe'


class ShoppingListView(LoginRequiredMixin, ListView):
    model = ShoppingList
    template_name = 'meal_planner/shopping-lists.html'
    context_object_name = 'shopping_lists'

    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)

    def post(self, request):
        if request.method == 'POST':
            delete_list = request.POST['delete_list']
            if delete_list:
                list = ShoppingList.objects.filter(user=self.request.user).filter(list_title=delete_list)
                list.delete()
        return redirect('shopping-lists')


class ShoppingDetailView(DetailView):
    model = ShoppingList
    template_name = 'meal_planner/shoppinglists_detail.html'

    def get_object(self, queryset=None):
        return ShoppingList.objects.filter(uuid=self.kwargs.get("uuid"))

    def get_context_data(self, **kwargs):
        shopping_list_title = ShoppingList.objects.filter(uuid=self.kwargs.get("uuid"))
        shopping_list = ShoppingListItems.objects.filter(list__uuid=self.kwargs.get("uuid")) \
            .values('recipe_ing_id__ingredient_id',
                    'recipe_ing_id__ingredient_id__ingredient_name',
                    'recipe_ing_id__ingredient_id__ingredient_aisle',
                    'recipe_ing_id__size',
                    'obtained') \
            .annotate(measurement_sum=Sum('recipe_ing_id__measurement')) \
            .order_by('recipe_ing_id__ingredient_id__ingredient_spoonacular')
        distinct_aisles = ShoppingListItems.objects.filter(list__uuid=self.kwargs.get("uuid")).values(
            'recipe_ing_id__ingredient_id__ingredient_aisle').distinct()
        aisle_list = []
        for d in distinct_aisles:
            aisle = d['recipe_ing_id__ingredient_id__ingredient_aisle']
            if aisle:
                aisle_split = aisle.split(';')
                for a in aisle_split:
                    if a not in aisle_list:
                        aisle_list.append(a)
        context = super(ShoppingDetailView, self).get_context_data(**kwargs)
        context['shopping_list_title'] = shopping_list_title[0].list_title
        context['shopping_list'] = shopping_list
        context['aisles'] = aisle_list
        return context

    def post(self, request, **kwargs):
        print(request.POST)
        obtained_true = request.POST.get('obtained_true')
        obtained_false = request.POST.get('obtained_false')
        delete_ing = request.POST.get('delete_ing')
        print(obtained_true)
        print(obtained_false)
        if delete_ing:
            ingredient = ShoppingListItems.objects.filter(list__uuid=self.kwargs.get("uuid")) \
                .get(recipe_ing_id__ingredient_id=delete_ing)
            ingredient.delete()
        elif obtained_true:
            ingredient = ShoppingListItems.objects.filter(list__uuid=self.kwargs.get("uuid")) \
                .get(recipe_ing_id__ingredient_id=obtained_true)
            ingredient.obtained = False
            ingredient.save()
        elif obtained_false:
            ingredient = ShoppingListItems.objects.filter(list__uuid=self.kwargs.get("uuid")) \
                .get(recipe_ing_id__ingredient_id=obtained_false)
            ingredient.obtained = True
            ingredient.save()
        return redirect(request.path)

        # x = 0
        # new_shopping_list = []
        # for obj in distinct_items:
        #     recipe_ing_id = obj['recipe_ing_id__ingredient_id']
        #     items = shopping_list.filter(recipe_ing_id__ingredient_id=recipe_ing_id)
        #     total_amount = items[0].recipe_ing_id.measurement
        #     for i in range(1, len(items)):
        #         new_amount = items[i].recipe_ing_id.measurement
        #         print(new_amount)
        #         if new_amount:
        #             if total_amount:
        #                 total_amount = total_amount + new_amount
        #             else:
        #                 total_amount = new_amount
        #             print(total_amount)
        #             print(new_amount)
        #     if total_amount:
        #         print(f" {total_amount.us_cup} cup(s) {items[0].recipe_ing_id.ingredient_id.ingredient_name} ")
        #         x += 1
        #         new_shopping_list.append(
        #             f" {round(total_amount.us_cup)} cup(s) {items[0].recipe_ing_id.ingredient_id.ingredient_name}")
        # print(x)

        # def get_queryset(self):
    #     return ShoppingListItems.objects.filter(list__uuid=self.kwargs.get("uuid"))


class MealPlanRedirectView(RedirectView):
    permanent = False
    query_string = False
    pattern_name = 'meal-plan-week'
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    url = f"{year}/{month}/{day}/"


class MealPlanCalendarView(LoginRequiredMixin, ListView):
    model = MealPlanCalendar
    template_name = 'meal_planner/meal-plan.html'

    def get_context_data(self, **kwargs):
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        week = datetime(year, month, day).isocalendar()[1]
        monday = date.fromisocalendar(year=year, week=week, day=1)
        week_dates = {}
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for weekday in weekdays:
            i = weekdays.index(weekday)
            week_date = monday + timedelta(days=i)
            week_dates.update({weekday: week_date})
        links = {}
        last_week = monday - timedelta(days=7)
        next_week = monday + timedelta(days=7)
        links.update({'last_week': last_week})
        links.update({'next_week': next_week})
        context = super().get_context_data(**kwargs)
        context['week_dates'] = week_dates
        context['links'] = links
        context['meal_plan'] = MealPlanCalendar.objects.filter(recipebox__user=self.request.user)
        context['courses'] = MealPlanCalendar.MEAL_CHOICES
        context['search_results'] = ShoppingList.objects.filter(user=self.request.user)
        return context

    def post(self, request, **kwargs):
        if request.method == 'POST':
            shopping_list_title = request.POST['shopping_list_title']
            if shopping_list_title:
                shoppinglist_instance = ShoppingList.objects.filter(list_title=shopping_list_title,
                                                                    user=self.request.user)
                if not shoppinglist_instance.exists():
                    shoppinglist_instance = ShoppingList.objects.create(list_title=shopping_list_title,
                                                                        user=self.request.user)
                else:
                    shoppinglist_instance = shoppinglist_instance[0]
                if shopping_list_title:
                    year = self.kwargs.get('year')
                    month = self.kwargs.get('month')
                    day = self.kwargs.get('day')
                    week = datetime(year, month, day).isocalendar()[1]
                    monday = date.fromisocalendar(year=year, week=week, day=1)
                    mealplan = MealPlanCalendar.objects.filter(start_week=monday)
                    print(mealplan)
                    for meal in mealplan:
                        recipe_id = meal.recipebox.recipe_id
                        ingredients = RecipeIngredients.objects.filter(recipe_id=recipe_id)
                        try:
                            for ingredient in ingredients:
                                ShoppingListItems.objects.create(list=shoppinglist_instance, recipe_ing_id=ingredient)
                            messages.success(request,
                                             f"Your shopping list has been updated with {ingredient.ingredient_id.ingredient_name}.")
                        except:
                            messages.error(request,
                                           f"Sorry, we were unable to add {ingredient.ingredient_id.ingredient_name} this to your shopping list.")
        return redirect('shopping-lists')


class MealPlanCreateView(LoginRequiredMixin, CreateView):
    template_name = 'meal_planner/meal_plan_add.html'
    form_class = MealPlanForm

    def get_form_kwargs(self):
        kwargs = super(MealPlanCreateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        if kwargs.get('data'):
            start_date = kwargs.get('data').get('start_date')
            end_date = kwargs.get('data').get('end_date')
            first_date = datetime.strptime(start_date, "%Y-%m-%d")
            sec_date = datetime.strptime(end_date, "%Y-%m-%d")
            initial_start_date = date(first_date.year, first_date.month, first_date.day)
            initial_end_date = date(sec_date.year, sec_date.month, sec_date.day)
            kwargs.update({'initial_start_date': initial_start_date})
            kwargs.update({'initial_end_date': initial_end_date})
            kwargs.update(
                {'redirect': f"/meal-planner/meal-plan/{first_date.year}/{first_date.month}/{first_date.day}/"})
        else:
            path_info = (self.request.path).split('/meal-planner/meal-plan/')[1].split('/')
            initial_start_date = date(int(path_info[0]), int(path_info[1]), int(path_info[2]))
            initial_end_date = date(int(path_info[0]), int(path_info[1]), int(path_info[2]))
            redirect = (self.request.path).split('add/')[0]
            kwargs.update({'initial_start_date': initial_start_date})
            kwargs.update({'initial_end_date': initial_end_date})
            kwargs.update({'redirect': redirect})
        return kwargs

    def get_success_url(self):
        """Return the URL to redirect to after processing a valid form."""
        self.success_url = self.get_form_kwargs().get('redirect')
        if not self.success_url:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return str(self.success_url)


def aboutus(request):
    return render(request, 'meal_planner/about-us.html')


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = "Website Inquiry"
            body = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'email': form.cleaned_data['email_address'],
                'message': form.cleaned_data['message'],
            }
            message = "\n".join(body.values())

            try:
                send_mail(subject, message, 'admin@example.com', ['admin@example.com'])
            except BadHeaderError:
                return HttpResponse('Invalid header found.')
            return redirect('home')

    form = ContactForm()
    return render(request, 'meal_planner/contact.html', {'form': form})


def privacypolicy(request):
    return render(request, 'meal_planner/privacy-policy.html')

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f"Thanks! Your account has been updated.")
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'meal_planner/profile.html', context)


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form_data = {
                'first_name': form.cleaned_data.get('firstname'),
                'last_name': form.cleaned_data.get('lastname'),
                'username': form.cleaned_data.get('username'),
                'email': form.cleaned_data.get('email'),
                'password': form.cleaned_data.get('password2')
            }
            new_user = User.objects.create_user(**form_data)
            new_user.save()

            messages.success(request, f"Welcome {form_data['first_name']}! You are now ready to login.")
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'meal_planner/register.html', {'form': form})


def add_recipes_links(request):
    if request.method == 'POST':
        url = request.POST['search-box']
        if url:
            try:
                recipe_data = spoonacular_api.extract_recipe(url)
            except IntegrityError:
                pass
            try:
                recipe_id = Recipes.objects.all().get(source_url=url)
                user = User.objects.all().get(username=request.user)
                try:
                    added_recipe = RecipeBox.objects.create(recipe_id=recipe_id, user=user)
                    recipe_ings = RecipeIngredients.objects.filter(recipe_id=recipe_id)
                    messages.success(request, f"Your recipe box has been updated.")
                    context = {'recipe_data': added_recipe,
                               'recipe_ings': recipe_ings}
                    return render(request, 'meal_planner/add-recipes-links.html', context)
                except IntegrityError:
                    messages.error(request, f"This recipe is already in your recipe box.")
                    return redirect('add-recipes-links')
            except Recipes.DoesNotExist:
                messages.error(request, f"There was an error trying to retrieve the recipe. \n"
                                        "The creator likely does not allow recipes to be copied.")
                return redirect('add-recipes-links')
        else:
            messages.error(request, f"Sorry, we were unable to add this to your recipe box.")
            return redirect('add-recipes-links')
    else:
        return render(request, 'meal_planner/add-recipes-links.html')


class AddRecipeFormView(LoginRequiredMixin, CreateView):
    model = Recipes
    fields = ['recipe_name', 'description', 'minutes', 'servings', 'instructions']
    template_name = 'meal_planner/add-recipes-personal.html'
    success_url = reverse_lazy('recipe-box')

    def get_context_data(self, **kwargs):
        recipes_form = CreateRecipesForm
        ing_form = IngredientsForm
        quant_form = RecipeIngredientsForm
        context = {'form': recipes_form,
                   'ing_form': ing_form,
                   'quant_form': quant_form}
        return context

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        quant = self.request.POST.getlist('measurement_0')
        measure = self.request.POST.getlist('measurement_1')
        ing_name = self.request.POST.getlist('ingredient_name')
        if form.is_valid():
            recipes = form.save(commit=False)
            recipes.credits_text = self.request.user.username
            recipes.ingredients = len(quant)
        try:
            recipes.save()
            recipebox = RecipeBox.objects.create(recipe_id=recipes, user=self.request.user)
            recipebox.save()
        except IntegrityError:
            print(recipes)
        for i in range(len(quant)):
            try:
                ingredient_instance = Ingredients.objects.get(ingredient_name=ing_name[i])
            except:
                ingredients = Ingredients(**{'ingredient_name': ing_name[i]})
                ingredients.save()
                ingredient_instance = Ingredients.objects.get(ingredient_id=ingredients.ingredient_id)
            rec_ingredients = RecipeIngredients(**{
                'ingredient_id': ingredient_instance,
                'recipe_id': recipes})
            q = convert_to_float(quant[i])
            unit = guess(q, measure[i], measures=[Volume])
            rec_ingredients.measurement = unit
            rec_ingredients.save()
        return super(AddRecipeFormView, self).form_valid(form)
