from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import os
import subprocess

from .models import HomePage, Recipe, Instruction
from .forms import RecipeForm, IngredientForm, InstructionsForm

def index(request):
    home_page = HomePage.objects.first()
    recipes = Recipe.objects.all()
    query = request.GET.get('q')
    meal_types = ['breakfast', 'lunch', 'dinner', 'dessert']
    if query:
        q_lower = query.lower().strip()
        if q_lower in meal_types:
            recipes = recipes.filter(meal_type=q_lower)
        else:
            found_meal = None
            for meal in meal_types:
                if meal in q_lower.split():
                    found_meal = meal
                    break
            if found_meal:
                recipes = recipes.filter(meal_type=found_meal)
            else:
                recipes = recipes.filter(
                    Q(title__icontains=query) |
                    Q(instructions__icontains=query) |
                    Q(ingredients__name__icontains=query)
                ).distinct()
    context = {
        'home_page': home_page,
        'recipes': recipes,
        'query': query or "",
        'meal_filter': "",
    }
    return render(request, 'recipes/index.html', context)

def add_recipe(request):
    form = RecipeForm()
    if request.method == "POST":
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Recipe created successfully!")
            return redirect("index")
    try:
        system_ip = subprocess.check_output(['hostname', '-I']).decode().strip().split()[0]
    except Exception:
        system_ip = None
    context = {
        'form': form,
        'system_ip': system_ip,
    }
    return render(request, "recipes/add_recipe.html", context)

def add_ingredient(request):
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = IngredientForm()
    return render(request, 'recipes/add_ingredient.html', {'form': form})

@login_required
def toggle_favorite(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    user = request.user
    if user in recipe.favorites.all():
        recipe.favorites.remove(user)
        messages.success(request, f"Removed '{recipe.title}' from your favorites.")
    else:
        recipe.favorites.add(user)
        messages.success(request, f"Added '{recipe.title}' to your favorites.")
    return redirect('index')

@login_required
def favorites(request):
    user = request.user
    recipes = Recipe.objects.filter(favorites=user)
    home_page = HomePage.objects.first()
    context = {
        'home_page': home_page,
        'recipes': recipes,
        'meal_filter': "",
        'query': "",
    }
    return render(request, 'recipes/index.html', context)

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)

def test_404(request):
    return render(request, 'recipes/404.html', status=404)

def splash(request):
    return render(request, "recipes/splash.html")

def splash_check(request):
    subprocess.run(
        ["ping", "-c", "1", "8.8.8.8"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return redirect('/')

@csrf_exempt
def shutdown(request):
    if request.method == 'POST':
        try:
            # suppress all kernel messages except panic
            subprocess.run(["sudo", "dmesg", "-n", "1"], check=True)
            # now power off
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
            return HttpResponse("Shutting down", status=200)
        except subprocess.CalledProcessError as e:
            return HttpResponse("Error: " + str(e), status=500)
    return HttpResponse("Method not allowed", status=405)


@csrf_exempt
def update_recipes(request):
    if request.method == "POST":
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        repo_dir = os.path.abspath(os.path.join(repo_dir, os.pardir))
        result = subprocess.run(
            ["git", "pull"], cwd=repo_dir,
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return JsonResponse({"status": "success", "output": result.stdout})
        else:
            return JsonResponse({"status": "error", "output": result.stderr})
    return HttpResponse("Method Not Allowed", status=405)

def instructions(request):
    instructions_list = Instruction.objects.all().order_by('-created_at')
    return render(request, 'recipes/instructions.html', {'instructions': instructions_list})

def add_intructions(request):
    from .forms import InstructionsForm
    form = InstructionsForm()
    if request.method == "POST":
        form = InstructionsForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Instructions added successfully!")
            return redirect("instructions")
    return render(request, "recipes/add_instructions.html", {'form': form})
