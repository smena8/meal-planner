from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import SelectDateWidget, NumberInput
from django_measurement.forms import MeasurementField, MeasurementWidget
from measurement.measures import Volume

from .models import Profile, RecipeBox, Recipes, MealPlanCalendar, Ingredients, RecipeIngredients


class ContactForm(forms.Form):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email_address = forms.EmailField(max_length=150)
    message = forms.CharField(widget=forms.Textarea, max_length=2000)


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    firstname = forms.CharField(max_length=20, required=True)
    lastname = forms.CharField(max_length=20, required=True)
    tnc = forms.BooleanField(required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'tnc']


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']


class CreateRecipesForm(forms.ModelForm):
    recipe_name = forms.CharField(max_length=100)
    description = forms.Textarea()
    minutes = forms.IntegerField()
    servings = forms.CharField(max_length=50, required=False)
    instructions = forms.Textarea()

    class Meta:
        model = Recipes
        fields = ['recipe_name', 'description', 'minutes', 'servings', 'instructions']


class IngredientsForm(forms.ModelForm):
    ingredient_name = forms.CharField(max_length=100)

    class Meta:
        model = Ingredients
        fields = ['ingredient_name']


class RecipeIngredientsForm(forms.ModelForm):
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
    measurement = forms.CharField(widget=MeasurementWidget(unit_choices=MEASURE_CHOICES))

    class Meta:
        model = RecipeIngredients
        fields = ['measurement']


class MealPlanForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        initial_start_date = kwargs.pop('initial_start_date')
        initial_end_date = kwargs.pop('initial_end_date')
        redirect = kwargs.pop('redirect')
        super(MealPlanForm, self).__init__(*args, **kwargs)
        self.fields['recipebox'].queryset = RecipeBox.objects.filter(user=user)
        self.fields["start_date"].initial = initial_start_date
        self.fields["end_date"].initial = initial_end_date

    recipebox = forms.ModelChoiceField(queryset=None,
                                       widget=forms.Select)
    start_date = forms.DateField(widget=NumberInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=NumberInput(attrs={'type': 'date'}))

    class Meta:
        model = MealPlanCalendar
        fields = '__all__'
        exclude = ['start_week', 'end_week', 'leftovers']
        autocomplete_fields = ['recipebox']
